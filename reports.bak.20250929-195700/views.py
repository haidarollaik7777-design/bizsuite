from django.db.models import Sum, Value, DecimalField
from django.conf import settings
from django.http import HttpResponse
from django.db.models.functions import Coalesce
from django.db.models import Sum, Value
from django.utils import timezone
from .utils.xlsx_export import rows_to_xlsx_response
from .utils.csv_export import rows_to_csv_response, safe_date
# reports/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.encoding import smart_str
from django.views.decorators.http import require_GET
import csv, importlib

VALID = {"trial-balance","general-ledger","balance-sheet","income-statement"}
TITLES = {
    "trial-balance": "Trial Balance",
    "general-ledger": "General Ledger",
    "balance-sheet": "Balance Sheet",
    "income-statement": "Income Statement",
}
CSV_NAMES = {
    "trial-balance": "trial_balance.csv",
    "general-ledger": "general_ledger.csv",
    "balance-sheet": "balance_sheet.csv",
    "income-statement": "income_statement.csv",
}

def _error_builder(msg):
    def _b(date_from=None, date_to=None):
        return {"title":"Report Error","columns":["error"],"rows":[{"error":msg}],
                "date_from":date_from,"date_to":date_to}
    return _b

def _builder(slug):
    try:
        rf = importlib.import_module("reports.reports_financial")
    except Exception as e:
        return _error_builder(f"Import reports_financial failed: {e!s}")
    name = {
        "trial-balance":"build_trial_balance",
        "general-ledger":"build_general_ledger",
        "balance-sheet":"build_balance_sheet",
        "income-statement":"build_income_statement",
    }[slug]
    fn = getattr(rf, name, None)
    return fn or _error_builder(f"Builder '{name}' missing in reports/reports_financial.py")

@staff_member_required
@require_GET
def report_center_proxy(request, report_id: str):
    if report_id not in VALID:
        raise Http404(f"Report with ID '{report_id}' doesn't exist.")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    fmt = (request.GET.get("format") or "").lower()

    builder = _builder(report_id)
    try:
        payload = builder(date_from=date_from, date_to=date_to)
    except Exception as e:
        payload = {"title":TITLES[report_id],"columns":["error"],
                   "rows":[{"error":f"Runtime error: {e!s}"}],
                   "date_from":date_from,"date_to":date_to}

    columns = payload.get("columns", [])
    rows = payload.get("rows", [])

    if fmt == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{smart_str(CSV_NAMES[report_id])}"'
        writer = csv.DictWriter(resp, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in columns})
        return resp

    return render(request, "reports/report_center_proxy.html", {
        "title": TITLES[report_id],
        "columns": columns,
        "rows": rows,
        "date_from": payload.get("date_from"),
        "date_to": payload.get("date_to"),
        "report_id": report_id,
        "debug_rows": None,
    })

def _is_csv(request):
    return (request.GET.get("format") or "").lower() == "csv"
def _want_xlsx(request):
    return (request.GET.get("format") or "").lower() in ("xlsx", "excel")
def _date_range(request):
    """
    Parses ?from=YYYY-MM-DD&to=YYYY-MM-DD, defaults to current month.
    """
    today = timezone.now().date()
    dfrom = request.GET.get("from")
    dto   = request.GET.get("to")
    if not dfrom or not dto:
        dfrom = today.replace(day=1)
        if today.month == 12:
            dto = today.replace(day=31)
        else:
            from datetime import timedelta
            import calendar
            last_day = calendar.monthrange(today.year, today.month)[1]
            dto = today.replace(day=last_day)
    else:
        dfrom = safe_date(dfrom, today.replace(day=1))
        dto   = safe_date(dto, today)
    return dfrom, dto
def report_general_ledger(request):
    """General Ledger page + CSV/XLSX export using Posting schema (fallback to JournalLine)."""
    try:
        Posting, date_f, debit_f, credit_f, acct_fk, AccountModel, code_f, name_f = _get_posting_schema()
    except Exception as e:
        return HttpResponse(f"Posting schema error: {e}", status=500, content_type="text/plain")

    dfrom, dto = _date_range(request)
    account_id  = request.GET.get("account")
    code_prefix = (request.GET.get("code_prefix") or "").strip()

    q = Posting.objects.select_related(acct_fk)
    q = q.filter(**{f"{date_f}__gte": dfrom, f"{date_f}__lte": dto})
    if account_id:
        q = q.filter(**{f"{acct_fk}_id": account_id})
    if code_prefix and code_f:
        q = q.filter(**{f"{acct_fk}__{code_f}__startswith": code_prefix})
    q = q.order_by(date_f, "id")

    # Build rows (shared)
    def _date_to_str(val):
        try:
            return val.isoformat()[:10] if hasattr(val, "isoformat") else (val or "")
        except Exception:
            return str(val or "")

    rows = []
    for p in q:
        dt = getattr(p, date_f.split("__")[0], None) if "__" not in date_f else None
        # robust: fetch via values dict when date is related (entry__date)
        if dt is None:
            # fallback: query value via dict approach
            from django.db.models import F, Value as V
        acct = getattr(p, acct_fk, None)
        code = getattr(acct, code_f, "") if acct is not None else ""
        name = getattr(acct, name_f, "") if acct is not None else ""
        deb  = getattr(p, debit_f, 0) or 0
        cre  = getattr(p, credit_f, 0) or 0
        memo = getattr(p, "memo", "") or ""
        # safer date fetch
        try:
            dval = getattr(p, date_f.replace("__", "_"), None)
            ds = _date_to_str(dval) if dval is not None else ""
        except Exception:
            ds = ""
        rows.append({"date": ds, "code": str(code), "name": str(name),
                     "deb": float(deb), "cre": float(cre), "memo": memo[:500]})

    if _is_csv(request):
        hdrs = ["Date","Code","Name","Debit","Credit","Memo"]
        data = [[r["date"], r["code"], r["name"], f"{r['deb']:.2f}", f"{r['cre']:.2f}", r["memo"]] for r in rows]
        return rows_to_csv_response(f"general_ledger_{dfrom}_to_{dto}", hdrs, data)
    if _want_xlsx(request):
        hdrs = ["Date","Code","Name","Debit","Credit","Memo"]
        data = [[r["date"], r["code"], r["name"], f"{r['deb']:.2f}", f"{r['cre']:.2f}", r["memo"]] for r in rows]
        return rows_to_xlsx_response(f"general_ledger_{dfrom}_to_{dto}", hdrs, data)

    # HTML
    context = {
        "lines": rows,
        "dfrom": dfrom, "dto": dto,
        "account_id": account_id, "code_prefix": code_prefix,
    }
    return render(request, "admin/accounting/reports/general_ledger.html", context)

def report_income_statement(request):
    return HttpResponse("Income Statement not implemented in this restore point.", status=501, content_type="text/plain")
def report_balance_sheet(request):
    return HttpResponse("Balance Sheet not implemented in this restore point.", status=501, content_type="text/plain")
def _get_posting_schema():
    """
    Resolve the Posting-like model & key fields.
    Preference order:
      1) settings.REPORTS_POSTING (e.g., ledger.Posting)
      2) Fallback to ledger.JournalLine with date='entry__date'
    Returns: PostingModel, date_f, debit_f, credit_f, acct_fk, AccountModel, code_f, name_f
    """
    from django.conf import settings
    from django.apps import apps

    # Defaults (used if settings points to missing model)
    Posting = None
    date_f, debit_f, credit_f, acct_fk = "date", "debit", "credit", "account"
    code_f = name_f = None

    # Try settings first
    cfg = getattr(settings, "REPORTS_POSTING", {}) or {}
    model_label = cfg.get("model")
    if model_label:
        try:
            app_label, model_name = model_label.split(".", 1)
            Posting = apps.get_model(app_label, model_name)
            date_f   = cfg.get("date",   date_f)
            debit_f  = cfg.get("debit",  debit_f)
            credit_f = cfg.get("credit", credit_f)
            acct_fk  = cfg.get("account",acct_fk)
        except Exception:
            Posting = None  # fall through to fallback

    # Fallback to ledger.JournalLine if needed
    if Posting is None:
        Posting = apps.get_model("ledger", "JournalLine")
        date_f  = "entry__date"
        debit_f = "debit"
        credit_f= "credit"
        acct_fk = "account"

    # Resolve Account model from FK
    acct_field = Posting._meta.get_field(acct_fk)
    AccountModel = acct_field.remote_field.model

    # Discover code/name fields
    acct_field_names = {f.name for f in AccountModel._meta.get_fields()}
    code_f = "code" if "code" in acct_field_names else None
    name_f = "name" if "name" in acct_field_names else None

    if not code_f:
        # fallback: first CharField
        from django.db.models import CharField
        for f in AccountModel._meta.get_fields():
            try:
                if isinstance(f, CharField):
                    code_f = f.name; break
            except Exception:
                pass
    if not name_f:
        for cand in ("title","label","description"):
            if cand in acct_field_names:
                name_f = cand; break
        if not name_f:
            name_f = code_f

    return Posting, date_f, debit_f, credit_f, acct_fk, AccountModel, code_f, name_f

        "rows": rows,
        "dfrom": dfrom, "dto": dto,
        "code_prefix": code_prefix,
        "total_deb": total_deb, "total_cre": total_cre,
        "balanced": abs(total_deb - total_cre) < 0.005,,
        "total_bal": total_deb - total_cre,
    request, "admin/accounting/reports/trial_balance.html", context)


def _posting_model_and_fields():
    # Uses settings.REPORTS_POSTING to discover the Posting model and field names
    from django.conf import settings
    from django.apps import apps as dj_apps
    cfg = getattr(settings, "REPORTS_POSTING", {
        "model": "ledger.Posting",
        "date": "date",
        "account": "account",
        "debit": "debit",
        "credit": "credit",
    })
    app_label, model_name = cfg["model"].split(".")
    Model = dj_apps.get_model(app_label, model_name)
    return Model, cfg
def report_trial_balance(request):
    from django.shortcuts import render
    from decimal import Decimal

    Posting, cfg = _posting_model_and_fields()

    dfrom, dto = _date_range(request)
    code_prefix = (request.GET.get("code_prefix") or "").strip()

    base = Posting.objects.filter(**{
        f"{cfg['date']}__gte": dfrom,
        f"{cfg['date']}__lte": dto,
    })
    if code_prefix:
        base = base.filter(**{f"{cfg['account']}__code__startswith": code_prefix})

    agg = (
        base.values("account_id", "account__code", "account__name")
            .annotate(
                deb=Coalesce(
                    Sum(cfg["debit"]),
                    Value(0, output_field=DecimalField(max_digits=18, decimal_places=2))
                ),
                cre=Coalesce(
                    Sum(cfg["credit"]),
                    Value(0, output_field=DecimalField(max_digits=18, decimal_places=2))
                ),
            )
            .order_by("account__code")
    )

    period = list(agg)

    total_deb = sum((r["deb"] or Decimal("0")) for r in period)
    total_cre = sum((r["cre"] or Decimal("0")) for r in period)
    total_bal = total_deb - total_cre
    balanced = abs(total_bal) < Decimal("0.005")

    # Build export rows
    export_rows = []
    for r in period:
        deb = r["deb"] or Decimal("0")
        cre = r["cre"] or Decimal("0")
        export_rows.append([
            r.get("account__code") or "",
            r.get("account__name") or "",
            f"{deb:.2f}",
            f"{cre:.2f}",
            f"{(deb - cre):.2f}",
        ])

    headers = ["Code", "Name", "Debit", "Credit", "Balance"]

    # CSV export
    if _is_csv(request):
        export_rows.append(["TOTALS","", f"{total_deb:.2f}", f"{total_cre:.2f}", f"{total_bal:.2f}"])
        return rows_to_csv_response(f"trial_balance_{dfrom}_to_{dto}", headers, export_rows)

    # XLSX export
    if _want_xlsx(request):
        export_rows.append(["TOTALS","", f"{total_deb:.2f}", f"{total_cre:.2f}", f"{total_bal:.2f}"])
        return rows_to_xlsx_response(f"trial_balance_{dfrom}_to_{dto}", headers, export_rows)

    # HTML page
    context = {
        "rows": period,
        "dfrom": dfrom,
        "dto": dto,
        "code_prefix": code_prefix,
        "total_deb": total_deb,
        "total_cre": total_cre,
        "total_bal": total_bal,
        "balanced": balanced,
    }
    return render(request, "admin/accounting/reports/trial_balance.html", context)


