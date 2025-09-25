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
    from django.shortcuts import render
    JournalLine = _get_JournalLine()
    dfrom, dto = _date_range(request)
    account_id  = request.GET.get("account")
    code_prefix = (request.GET.get("code_prefix") or "").strip()

    entry_fk, EntryModel = _detect_entry_relation_and_fields(JournalLine)
    acct_fk, AccountModel, code_field, name_field = _detect_account_relation_and_fields(JournalLine)

    sel = []
    if entry_fk: sel.append(entry_fk)
    if acct_fk:  sel.append(acct_fk)
    q = JournalLine.objects.select_related(*sel)

    ef = _build_entry_filters(entry_fk, EntryModel, dfrom, dto)
    if ef: q = q.filter(**ef)
    if account_id:
        q = q.filter(**{f"{acct_fk}_id": account_id}) if acct_fk else q
    if code_prefix and acct_fk and code_field:
        q = q.filter(**{f"{acct_fk}__{code_field}__startswith": code_prefix})

    q = q.order_by("id")

    # Build export rows
    headers = ["Date","Code","Name","Debit","Credit","Memo"]
    # date attr (best effort)
    entry_date_attr = None
    if entry_fk and EntryModel:
        for nm in ("date","posting_date","entry_date","txn_date","transaction_date","posted_on","created","created_at"):
            try:
                EntryModel._meta.get_field(nm); entry_date_attr = nm; break
            except Exception: pass

    rows = []
    for ln in q:
        # date
        if entry_fk and entry_date_attr:
            try:
                eobj = getattr(ln, entry_fk, None)
                dval = getattr(eobj, entry_date_attr, None)
                dstr = dval.isoformat() if dval else ""
            except Exception:
                dstr = ""
        else:
            dstr = ""
        # account code/name
        try:
            aobj = getattr(ln, acct_fk) if acct_fk else None
            code = getattr(aobj, code_field) if (aobj and code_field) else ""
            name = getattr(aobj, name_field) if (aobj and name_field) else ""
        except Exception:
            code = ""; name = ""

        rows.append([
            dstr, str(code), str(name),
            f"{float(getattr(ln,'debit',0) or 0):.2f}",
            f"{float(getattr(ln,'credit',0) or 0):.2f}",
            (getattr(ln,'memo',None) or getattr(getattr(ln, entry_fk, None),'memo',None) or '')[:500] if entry_fk else (getattr(ln,'memo','') or '')[:500],
        ])

    if _is_csv(request):
        return rows_to_csv_response(f"general_ledger_{dfrom}_to_{dto}", headers, rows)
    if _want_xlsx(request):
        return rows_to_xlsx_response(f"general_ledger_{dfrom}_to_{dto}", headers, rows)

    context = {"lines": q, "dfrom": dfrom, "dto": dto, "account_id": account_id, "code_prefix": code_prefix}
    return render(request, "admin/accounting/reports/general_ledger.html", context)
def report_trial_balance(request):
    from django.shortcuts import render
    from django.db.models import Sum, Value
    from django.db.models.functions import Coalesce

    JournalLine = _get_JournalLine()
    dfrom, dto = _date_range(request)
    code_prefix = (request.GET.get("code_prefix") or "").strip()

    entry_fk, EntryModel = _detect_entry_relation_and_fields(JournalLine)
    acct_fk, AccountModel, code_field, name_field = _detect_account_relation_and_fields(JournalLine)

    q = JournalLine.objects.all()
    ef = _build_entry_filters(entry_fk, EntryModel, dfrom, dto)
    if ef: q = q.filter(**ef)
    if code_prefix and acct_fk and code_field:
        q = q.filter(**{f"{acct_fk}__{code_field}__startswith": code_prefix})

    vals = []
    if acct_fk and code_field: vals.append(f"{acct_fk}__{code_field}")
    if acct_fk and name_field: vals.append(f"{acct_fk}__{name_field}")
    if not vals: vals = ["id"]  # fallback to avoid crash

    period = (q.values(*([f"{acct_fk}_id"] if acct_fk else ["id"]), *vals)
                .annotate(deb=Coalesce(Sum("debit"), Value(0)),
                          cre=Coalesce(Sum("credit"), Value(0)))
                .order_by(*vals))

    rows_display, rows_export = [], []
    total_deb = total_cre = 0.0
    for r in period:
        deb = float(r["deb"] or 0.0); cre = float(r["cre"] or 0.0); bal = deb - cre
        total_deb += deb; total_cre += cre
        c = r.get(f"{acct_fk}__{code_field}", "") if acct_fk and code_field else ""
        n = r.get(f"{acct_fk}__{name_field}", "") if acct_fk and name_field else ""
        rows_display.append({"account__code": c, "account__name": n, "deb": deb, "cre": cre, "balance": bal})
        rows_export.append([c, n, f"{deb:.2f}", f"{cre:.2f}", f"{bal:.2f}"])

    headers = ["Code","Name","Debit","Credit","Balance"]
    total_net = total_deb - total_cre
    if _is_csv(request):
        rows_export.append(["TOTALS","", f"{total_deb:.2f}", f"{total_cre:.2f}", f"{total_net:.2f}"])
        return rows_to_csv_response(f"trial_balance_{dfrom}_to_{dto}", headers, rows_export)
    if _want_xlsx(request):
        rows_export.append(["TOTALS","", f"{total_deb:.2f}", f"{total_cre:.2f}", f"{total_net:.2f}"])
        return rows_to_xlsx_response(f"trial_balance_{dfrom}_to_{dto}", headers, rows_export)

    context = {"rows": rows_display, "dfrom": dfrom, "dto": dto, "code_prefix": code_prefix,
               "total_deb": total_deb, "total_cre": total_cre, "total_net": total_net,
               "balanced": abs(total_net) < 0.005}
    return render(request, "admin/accounting/reports/trial_balance.html", context)
def report_income_statement(request):
    from django.shortcuts import render
    from django.db.models import Sum, Value
    from django.db.models.functions import Coalesce

    JournalLine = _get_JournalLine()
    dfrom, dto = _date_range(request)
    code_prefix = (request.GET.get("code_prefix") or "").strip()

    entry_fk, EntryModel = _detect_entry_relation_and_fields(JournalLine)
    acct_fk, AccountModel, code_field, name_field = _detect_account_relation_and_fields(JournalLine)

    q = JournalLine.objects.all()
    ef = _build_entry_filters(entry_fk, EntryModel, dfrom, dto)
    if ef: q = q.filter(**ef)
    if code_prefix and acct_fk and code_field:
        q = q.filter(**{f"{acct_fk}__{code_field}__startswith": code_prefix})

    vals = []
    if acct_fk and code_field: vals.append(f"{acct_fk}__{code_field}")
    if acct_fk and name_field: vals.append(f"{acct_fk}__{name_field}")
    if not vals: vals = ["id"]

    agg = (q.values(*([f"{acct_fk}_id"] if acct_fk else ["id"]), *vals)
             .annotate(deb=Coalesce(Sum("debit"), Value(0)),
                       cre=Coalesce(Sum("credit"), Value(0)))
             .order_by(*vals))

    revenue_rows, expense_rows = [], []
    total_rev = total_exp = 0.0

    for r in agg:
        code = str(r.get(f"{acct_fk}__{code_field}", "")) if acct_fk and code_field else ""
        name = str(r.get(f"{acct_fk}__{name_field}", "")) if acct_fk and name_field else ""
        deb = float(r["deb"] or 0.0)
        cre = float(r["cre"] or 0.0)

        lcname = name.lower()
        is_rev = (code.startswith("4")) or ("revenue" in lcname)
        is_exp = (code.startswith("5")) or ("expense" in lcname or "expenses" in lcname)

        if is_rev:
            amt = cre - deb; total_rev += amt; revenue_rows.append([code, name, f"{amt:.2f}"])
        elif is_exp:
            amt = deb - cre; total_exp += amt; expense_rows.append([code, name, f"{amt:.2f}"])
        else:
            amt = deb - cre; total_exp += amt; expense_rows.append([code, name, f"{amt:.2f}"])

    net_income = total_rev - total_exp

    headers = ["Code","Name","Amount"]
    rows_export = [["Revenue","",""]]
    rows_export += (revenue_rows or [["(No rows)","","0.00"]])
    rows_export.append(["Total Revenue","","{:.2f}".format(total_rev)])
    rows_export.append(["Expenses","",""])
    rows_export += (expense_rows or [["(No rows)","","0.00"]])
    rows_export.append(["Total Expenses","","{:.2f}".format(total_exp)])
    rows_export.append(["Net Income","","{:.2f}".format(net_income)])

    if _is_csv(request):
        return rows_to_csv_response(f"income_statement_{dfrom}_to_{dto}", headers, rows_export)
    if _want_xlsx(request):
        return rows_to_xlsx_response(f"income_statement_{dfrom}_to_{dto}", headers, rows_export)

    context = {"dfrom": dfrom, "dto": dto, "code_prefix": code_prefix,
               "revenue_rows": revenue_rows, "expense_rows": expense_rows,
               "total_rev": total_rev, "total_exp": total_exp, "net_income": net_income}
    return render(request, "admin/accounting/reports/income_statement.html", context)
def _dispatch_export(request, report_id: str, fmt: str):
    url_map = {
        "trial-balance":  "/admin/reports/trial-balance/",
        "general-ledger": "/admin/reports/general-ledger/",
        "income-statement": "/admin/reports/income-statement/",
    }
    target = url_map.get(report_id)
    if not target:
        raise Http404(f"Unknown report: {report_id}")
    qs = request.META.get("QUERY_STRING", "")
    params = {}
    if qs:
        try:
            params = dict(parse_qsl(qs, keep_blank_values=True))
        except Exception:
            return redirect(f"{target}?{qs}&format={fmt}" if qs else f"{target}?format={fmt}")
    params["format"] = fmt
    return redirect(f"{target}?{urlencode(params)}")

def export_xlsx_dispatch(request, report_id: str):
    return _dispatch_export(request, report_id, "xlsx")

def export_csv_dispatch(request, report_id: str):
    return _dispatch_export(request, report_id, "csv")

def _get_JournalLine():
    """
    Return the Journal Line model by scanning common app/model names.
    Adjust the candidate list to your schema if needed.
    """
    from django.apps import apps as djapps
    candidates = [
        ("accounting", "JournalLine"),
        ("ledger",     "JournalLine"),
        ("accounting", "JournalEntryLine"),
        ("ledger",     "JournalEntryLine"),
    ]
    for app_label, model_name in candidates:
        try:
            M = djapps.get_model(app_label, model_name)
            if M is not None:
                return M
        except LookupError:
            pass
    raise LookupError("Could not find a Journal Line model. Tried: " + ", ".join([f"{a}.{m}" for a,m in candidates]))

def _detect_entry_relation_and_fields(JournalLine):
    """
    Returns (entry_fk_name, EntryModel). Tries common FK names, then heuristics.
    """
    from django.db.models import ForeignKey
    # Try common names first
    for cand in ("entry", "journal_entry", "move", "voucher", "document"):
        try:
            f = JournalLine._meta.get_field(cand)
            if getattr(f, "is_relation", False):
                return f.name, f.related_model
        except Exception:
            pass
    # Heuristic: first FK whose related model name mentions entry/journal
    for f in JournalLine._meta.get_fields():
        if getattr(f, "is_relation", False) and getattr(f, "many_to_one", False):
            rm = getattr(f, "related_model", None)
            if rm:
                name = (rm.__name__ + " " + getattr(getattr(rm, "_meta", None), "verbose_name", "")).lower()
                if "entry" in name or "journal" in name:
                    return f.name, rm
    # Fallback: first FK at all
    for f in JournalLine._meta.get_fields():
        if getattr(f, "is_relation", False) and getattr(f, "many_to_one", False):
            return f.name, f.related_model
    return None, None

def _build_entry_filters(entry_fk, EntryModel, dfrom, dto):
    """
    Builds safe filters dict for date range and posted flag if available.
    Never references non-existent fields.
    """
    filters = {}
    if not entry_fk or not EntryModel:
        return filters

    # Date field detection
    from django.db.models import DateField, DateTimeField
    date_name = None
    for nm in ("date", "posting_date", "entry_date", "txn_date", "transaction_date", "posted_on", "created", "created_at"):
        try:
            f = EntryModel._meta.get_field(nm)
            if isinstance(f, (DateField, DateTimeField)):
                date_name = nm
                break
        except Exception:
            pass
    if not date_name:
        # First Date/DateTime field if any
        for f in EntryModel._meta.get_fields():
            try:
                if isinstance(f, (DateField, DateTimeField)):
                    date_name = f.name
                    break
            except Exception:
                pass
    if date_name:
        filters[f"{entry_fk}__{date_name}__gte"] = dfrom
        filters[f"{entry_fk}__{date_name}__lte"] = dto

    # Posted boolean (optional)
    for nm in ("is_posted", "posted", "is_finalized", "is_approved", "posted_flag"):
        try:
            f = EntryModel._meta.get_field(nm)
            # BooleanField check by name to avoid importing types
            if getattr(f, "get_internal_type", lambda: "")() == "BooleanField":
                filters[f"{entry_fk}__{nm}"] = True
                break
        except Exception:
            pass

    return filters
def _detect_account_relation_and_fields(JournalLine):
    """
    Returns (account_fk_name, AccountModel, code_field, name_field).
    Detects the FK to the account model and the best code/name fields on that model.
    """
    # 1) Find account FK
    acct_fk = None
    AccountModel = None
    # Try common FK names first
    for cand in ("account","acct","ledger_account","gl_account","account_ref"):
        try:
            f = JournalLine._meta.get_field(cand)
            if getattr(f, "is_relation", False) and getattr(f, "many_to_one", False):
                acct_fk, AccountModel = f.name, f.related_model
                break
        except Exception:
            pass
    # Heuristic: first FK whose related model name mentions 'account'
    if not acct_fk:
        for f in JournalLine._meta.get_fields():
            if getattr(f, "is_relation", False) and getattr(f, "many_to_one", False):
                rm = getattr(f, "related_model", None)
                if rm:
                    name = (rm.__name__ + " " + getattr(getattr(rm, "_meta", None), "verbose_name", "")).lower()
                    if "account" in name or "ledger" in name:
                        acct_fk, AccountModel = f.name, rm
                        break
    # Fallback: first FK at all
    if not acct_fk:
        for f in JournalLine._meta.get_fields():
            if getattr(f, "is_relation", False) and getattr(f, "many_to_one", False):
                acct_fk, AccountModel = f.name, f.related_model
                break

    # 2) Pick code/name fields on Account model
    code_field = None
    name_field = None
    code_candidates = ("code","number","no","account_code","acct_code","id_code")
    name_candidates = ("name","title","account_name","description","label")

    def _has_field(model, fname):
        try:
            model._meta.get_field(fname)
            return True
        except Exception:
            return False

    for nm in code_candidates:
        if AccountModel and _has_field(AccountModel, nm):
            code_field = nm; break
    for nm in name_candidates:
        if AccountModel and _has_field(AccountModel, nm):
            name_field = nm; break

    # Last-resort fallbacks
    if not code_field and AccountModel:
        # first CharField-ish
        for f in AccountModel._meta.get_fields():
            if getattr(f, "get_internal_type", lambda: "")() in ("CharField","TextField"):
                code_field = f.name; break
    if not name_field:
        name_field = code_field or "id"

    return acct_fk, AccountModel, code_field, name_field