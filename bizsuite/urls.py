from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils.encoding import smart_str
from decimal import Decimal
from io import BytesIO
import csv
from urllib.parse import urlencode
from collections import defaultdict, OrderedDict

from django.apps import apps
from django.conf import settings
from django.db.models import Sum, Value as V, DecimalField
from django.db.models.functions import Coalesce
from reports.exporters import gl_xlsx, tb_xlsx, bs_xlsx, is_xlsx

# ------------ helpers ------------

def _fmt(x):
    try:
        return f"{Decimal(x):,.2f}"
    except Exception:
        return str(x)

def _xlsx_response(filename, sheet_name, headers, rows, extras=None):
    try:
        from openpyxl import Workbook
    except Exception:
        return HttpResponse("openpyxl not installed. Run: pip install openpyxl", status=500)
    wb = Workbook()
    ws = wb.active
    ws.title = (sheet_name or "Sheet")[:31]
    if headers:
        ws.append(headers)
    for r in rows:
        ws.append(r)
    # extras: list of (title, headers, rows) for extra sheets (e.g., subtotals)
    if extras:
        for title, h, r in extras:
            ws2 = wb.create_sheet(title[:31])
            if h: ws2.append(h)
            for rr in r:
                ws2.append(rr)
    bio = BytesIO()
    wb.save(bio); bio.seek(0)
    resp = HttpResponse(bio.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{smart_str(filename)}"'
    return resp

def _resolve_model_and_fields():
    """
    Returns: (Model, account_field, debit_field, credit_field, date_lookup)
    Prefers ledger.JournalLine; otherwise uses settings.REPORTS_POSTING.
    date_lookup may be "date", "entry__date", or None.
    """
    Model = None
    account_field = "account"
    debit_field = "debit"
    credit_field = "credit"
    date_lookup = "date"

    try:
        Model = apps.get_model("ledger", "JournalLine")
    except Exception:
        Model = None

    if Model is None:
        conf = getattr(settings, "REPORTS_POSTING", {}) or {}
        mpath = conf.get("model", "")
        if not mpath or "." not in mpath:
            return None, account_field, debit_field, credit_field, None
        app_label, model_name = mpath.split(".")
        try:
            Model = apps.get_model(app_label, model_name)
        except Exception:
            return None, account_field, debit_field, credit_field, None
        account_field = conf.get("account", account_field)
        debit_field = conf.get("debit", debit_field)
        credit_field = conf.get("credit", credit_field)
        date_lookup = conf.get("date", "date")

    try:
        field_names = {f.name for f in Model._meta.get_fields()}
    except Exception:
        field_names = set()
    if "date" not in field_names and "entry" in field_names:
        date_lookup = "entry__date"
    elif "date" not in field_names:
        date_lookup = None

    return Model, account_field, debit_field, credit_field, date_lookup

def _require_group(user):
    # Optional hardening: set REPORTS_REQUIRE_GROUP=True in settings to enforce 'ReportViewers'
    need = getattr(settings, "REPORTS_REQUIRE_GROUP", False)
    if not need:
        return True
    try:
        return user.is_active and user.is_staff and (user.is_superuser or user.groups.filter(name="ReportViewers").exists())
    except Exception:
        return False

# ------------ views ------------

def report_general_ledger(request):
    if not _require_group(request.user):
        return HttpResponse("Forbidden (ReportViewers required)", status=403)

    # Prefer JournalLine; else configured model
    Model = None
    try:
        Model = apps.get_model("ledger", "JournalLine")
    except Exception:
        Model = None
    if Model is None:
        conf = getattr(settings, "REPORTS_POSTING", None)
        if not conf or "model" not in conf:
            return HttpResponse("General Ledger configuration missing (REPORTS_POSTING).", status=500)
        app_label, model_name = conf["model"].split(".")
        try:
            Model = apps.get_model(app_label, model_name)
        except Exception as e:
            return HttpResponse(f"Cannot load posting model: {e!s}", status=500)

    # Base queryset
    try:
        qs_base = Model.objects.select_related("account", "entry")
    except Exception:
        try:
            qs_base = Model.objects.select_related("account")
        except Exception:
            qs_base = Model.objects.all()

    # Filters
    df = request.GET.get("date_from")
    dt = request.GET.get("date_to")
    acct_code = (request.GET.get("account_code") or "").strip()

    # Dates
    tried_direct = False
    if df or dt:
        try:
            if df: qs_base = qs_base.filter(date__gte=df)
            if dt: qs_base = qs_base.filter(date__lte=dt)
            tried_direct = True
        except Exception:
            tried_direct = False
    if (df or dt) and not tried_direct:
        try:
            if df: qs_base = qs_base.filter(entry__date__gte=df)
            if dt: qs_base = qs_base.filter(entry__date__lte=dt)
        except Exception:
            pass

    # Account prefix
    if acct_code:
        try:
            qs_base = qs_base.filter(account__code__startswith=acct_code)
        except Exception:
            pass

    # Ordering
    try:
        qs_ordered = qs_base.order_by("date", "id")
    except Exception:
        try:
            qs_ordered = qs_base.order_by("entry__date", "id")
        except Exception:
            qs_ordered = qs_base.order_by("id")

    # Pagination
    def _i(v, d):
        try:
            n = int(v); return n if n > 0 else d
        except Exception:
            return d
    page = _i(request.GET.get("page"), 1)
    page_size = _i(request.GET.get("page_size"), 200)
    if page_size < 20: page_size = 20
    if page_size > 1000: page_size = 1000

    total_count = qs_ordered.count()
    start = (page - 1) * page_size
    stop = start + page_size
    qs = qs_ordered[start:stop]

    has_prev = page > 1
    has_next = stop < total_count
    total_pages = (total_count + page_size - 1) // page_size

    def build_page_qs(new_page):
        q = request.GET.copy()
        q["page"] = str(new_page)
        q["page_size"] = str(page_size)
        items = []
        for k in ["date_from","date_to","account_code","page","page_size","format"]:
            if k in q and q[k] not in (None,""):
                items.append((k, q[k]))
        return "?" + urlencode(items)

    prev_qs = build_page_qs(page - 1) if has_prev else ""
    next_qs = build_page_qs(page + 1) if has_next else ""

    rows = []
    for obj in qs:
        dr = getattr(obj, "debit", None) or Decimal("0")
        cr = getattr(obj, "credit", None) or Decimal("0")
        dval = getattr(obj, "date", None)
        if not dval:
            ent = getattr(obj, "entry", None)
            dval = getattr(ent, "date", "") if ent else ""
        acct = getattr(obj, "account", None)
        code = getattr(acct, "code", "") if acct else ""
        name = getattr(acct, "name", "") if acct else ""
        memo = getattr(obj, "memo", "") or getattr(obj, "label", "") or ""
        rows.append({"date": dval, "code": code, "name": name, "debit": dr, "credit": cr, "memo": memo})

    fmt = (request.GET.get("format") or "").lower()
    if fmt == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{smart_str("general_ledger.csv")}"'
        w = csv.writer(resp); w.writerow(["date","code","name","debit","credit","memo"])
        for r in rows: w.writerow([r["date"], r["code"], r["name"], r["debit"], r["credit"], r["memo"]])
        return resp
    if fmt == "xlsx":
        data = [[r["date"], r["code"], r["name"], float(r["debit"]), float(r["credit"]), r["memo"]] for r in rows]
        return _xlsx_response("general_ledger.xlsx", "General Ledger",
                              ["date","code","name","debit","credit","memo"], data)

    return render(request, "admin/accounting/reports/general_ledger.html", {
        **admin.site.each_context(request),
        "title": "General Ledger",
        "rows": rows,
        "date_from": df,
        "date_to": dt,
        "account_code": acct_code,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "has_prev": has_prev,
        "has_next": has_next,
        "prev_qs": prev_qs,
        "next_qs": next_qs,
    })

def report_trial_balance(request):
    if not _require_group(request.user):
        return HttpResponse("Forbidden (ReportViewers required)", status=403)

    Model, account_field, debit_field, credit_field, date_lookup = _resolve_model_and_fields()
    if Model is None:
        return HttpResponse("Cannot resolve posting model for Trial Balance.", status=500)

    qs = Model.objects.all()
    df = request.GET.get("date_from")
    dt = request.GET.get("date_to")
    try:
        if date_lookup and df: qs = qs.filter(**{f"{date_lookup}__gte": df})
        if date_lookup and dt: qs = qs.filter(**{f"{date_lookup}__lte": dt})
    except Exception:
        pass

    code_path = f"{account_field}__code"
    name_path = f"{account_field}__name"
    ann = qs.values(code_path, name_path).annotate(
        dr=Coalesce(Sum(debit_field),  V(Decimal("0.00")), output_field=DecimalField(max_digits=18, decimal_places=2)),
        cr=Coalesce(Sum(credit_field), V(Decimal("0.00")), output_field=DecimalField(max_digits=18, decimal_places=2)),
    ).order_by(code_path)

    rows = []
    tot_deb = Decimal("0"); tot_cr = Decimal("0")
    for a in ann:
        code = str(a.get(code_path) or "")
        name = a.get(name_path) or ""
        if not code: continue
        bal = (a["dr"] or Decimal("0")) - (a["cr"] or Decimal("0"))
        debit_col  = bal if bal > 0 else Decimal("0")
        credit_col = -bal if bal < 0 else Decimal("0")
        rows.append({"code": code, "name": name, "debit": _fmt(debit_col), "credit": _fmt(credit_col), "balance": _fmt(bal)})
        tot_deb += debit_col; tot_cr += credit_col

    fmt = (request.GET.get("format") or "").lower()
    if fmt == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{smart_str("trial_balance.csv")}"'
        w = csv.writer(resp)
        w.writerow(["code","name","debit","credit","balance"])
        for r in rows: w.writerow([r["code"], r["name"], r["debit"], r["credit"], r["balance"]])
        w.writerow(["","TOTALS", _fmt(tot_deb), _fmt(tot_cr), _fmt(tot_deb - tot_cr)])
        return resp
    if fmt == "xlsx":
        data = [[r["code"], r["name"], float(str(r["debit"]).replace(',','')), float(str(r["credit"]).replace(',','')), float(str(r["balance"]).replace(',',''))] for r in rows]
        return _xlsx_response("trial_balance.xlsx", "Trial Balance",
                              ["code","name","debit","credit","balance"], data)

    return render(request, "admin/accounting/reports/trial_balance.html", {
        **admin.site.each_context(request),
        "title": "Trial Balance",
        "rows": rows,
        "tot_deb": _fmt(tot_deb),
        "tot_cr": _fmt(tot_cr),
        "date_from": df, "date_to": dt,
    })

def report_balance_sheet(request):
    if not _require_group(request.user):
        return HttpResponse("Forbidden (ReportViewers required)", status=403)

    Model, account_field, debit_field, credit_field, date_lookup = _resolve_model_and_fields()
    if Model is None:
        return HttpResponse("Cannot resolve posting model for Balance Sheet.", status=500)

    qs = Model.objects.all()
    dt = request.GET.get("date_to")
    try:
        if date_lookup and dt: qs = qs.filter(**{f"{date_lookup}__lte": dt})
    except Exception:
        pass

    code_path = f"{account_field}__code"
    name_path = f"{account_field}__name"
    ann = qs.values(code_path, name_path).annotate(
        dr=Coalesce(Sum(debit_field),  V(Decimal("0.00")), output_field=DecimalField(max_digits=18, decimal_places=2)),
        cr=Coalesce(Sum(credit_field), V(Decimal("0.00")), output_field=DecimalField(max_digits=18, decimal_places=2)),
    ).order_by(code_path)

    assets = []; liab = []; equity = []
    tot_assets = Decimal("0"); tot_liab = Decimal("0"); tot_equity = Decimal("0")
    famlen = 2  # family by first 2 digits
    famA = defaultdict(Decimal); famL = defaultdict(Decimal); famE = defaultdict(Decimal)

    for a in ann:
        code = str(a.get(code_path) or "")
        if not code: continue
        name = a.get(name_path) or ""
        head = code.strip()[0]
        dr = a["dr"] or Decimal("0"); cr = a["cr"] or Decimal("0")
        if head == "1":     # Assets (debit)
            amt = dr - cr
            if amt:
                assets.append({"code": code, "name": name, "balance": _fmt(amt)})
                tot_assets += amt
                famA[code[:famlen]] += amt
        elif head == "2":   # Liabilities (credit)
            amt = cr - dr
            if amt:
                liab.append({"code": code, "name": name, "balance": _fmt(amt)})
                tot_liab += amt
                famL[code[:famlen]] += amt
        elif head == "3":   # Equity (credit)
            amt = cr - dr
            if amt:
                equity.append({"code": code, "name": name, "balance": _fmt(amt)})
                tot_equity += amt
                famE[code[:famlen]] += amt

    # retained earnings
    rev_total = Decimal("0"); exp_total = Decimal("0")
    for a in ann:
        code = str(a.get(code_path) or ""); 
        if not code: continue
        head = code.strip()[0]
        dr = a["dr"] or Decimal("0"); cr = a["cr"] or Decimal("0")
        if head in ("4","7"): rev_total += (cr - dr)
        elif head in ("5","6","8","9"): exp_total += (dr - cr)
    net_income = rev_total - exp_total
    if net_income:
        equity.append({"code": "", "name": "Retained Earnings (to date)", "balance": _fmt(net_income)})
        tot_equity += net_income

    tot_liab_equity = tot_liab + tot_equity

    # family subtotals
    assets_fam = [[k, _fmt(v)] for k, v in sorted(famA.items())]
    liab_fam   = [[k, _fmt(v)] for k, v in sorted(famL.items())]
    equity_fam = [[k, _fmt(v)] for k, v in sorted(famE.items())]

    fmt = (request.GET.get("format") or "").lower()
    if fmt == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{smart_str("balance_sheet.csv")}"'
        w = csv.writer(resp)
        w.writerow(["section","code","name","amount"])
        for r in assets: w.writerow(["Assets", r["code"], r["name"], r["balance"]])
        w.writerow(["Totals","","Total Assets", _fmt(tot_assets)])
        for r in liab:   w.writerow(["Liabilities", r["code"], r["name"], r["balance"]])
        for r in equity: w.writerow(["Equity", r["code"], r["name"], r["balance"]])
        w.writerow(["Totals","","Total Liabilities + Equity", _fmt(tot_liab_equity)])
        return resp
    if fmt == "xlsx":
        details = []
        for r in assets: details.append(["Assets", r["code"], r["name"], r["balance"]])
        details.append(["Totals","","Total Assets", _fmt(tot_assets)])
        for r in liab:   details.append(["Liabilities", r["code"], r["name"], r["balance"]])
        for r in equity: details.append(["Equity", r["code"], r["name"], r["balance"]])
        details.append(["Totals","","Total Liabilities + Equity", _fmt(tot_liab_equity)])
        extras = [
            ("Assets Subtotals", ["family","amount"], assets_fam),
            ("Liabilities Subtotals", ["family","amount"], liab_fam),
            ("Equity Subtotals", ["family","amount"], equity_fam),
        ]
        return _xlsx_response("balance_sheet.xlsx", "Balance Sheet",
                              ["section","code","name","amount"], details, extras=extras)

    return render(request, "admin/accounting/reports/balance_sheet.html", {
        **admin.site.each_context(request),
        "title": "Balance Sheet",
        "date_to": dt,
        "assets": assets, "liabilities": liab, "equity": equity,
        "tot_assets": _fmt(tot_assets), "tot_liab": _fmt(tot_liab),
        "tot_equity": _fmt(tot_equity), "tot_liab_equity": _fmt(tot_liab_equity),
        "assets_fam": assets_fam, "liab_fam": liab_fam, "equity_fam": equity_fam,
    })

def report_income_statement(request):
    if not _require_group(request.user):
        return HttpResponse("Forbidden (ReportViewers required)", status=403)

    Model, account_field, debit_field, credit_field, date_lookup = _resolve_model_and_fields()
    if Model is None:
        return HttpResponse("Cannot resolve posting model for Income Statement.", status=500)

    qs = Model.objects.all()
    df = request.GET.get("date_from"); dt = request.GET.get("date_to")
    try:
        if date_lookup and df: qs = qs.filter(**{f"{date_lookup}__gte": df})
        if date_lookup and dt: qs = qs.filter(**{f"{date_lookup}__lte": dt})
    except Exception:
        pass

    code_path = f"{account_field}__code"; name_path = f"{account_field}__name"
    ann = qs.values(code_path, name_path).annotate(
        dr=Coalesce(Sum(debit_field),  V(Decimal("0.00")), output_field=DecimalField(max_digits=18, decimal_places=2)),
        cr=Coalesce(Sum(credit_field), V(Decimal("0.00")), output_field=DecimalField(max_digits=18, decimal_places=2)),
    ).order_by(code_path)

    revenue = []; expense = []
    tot_rev = Decimal("0"); tot_exp = Decimal("0")
    famlen = 2
    famR = defaultdict(Decimal); famE = defaultdict(Decimal)

    for a in ann:
        code = str(a.get(code_path) or ""); 
        if not code: continue
        name = a.get(name_path) or ""
        head = code.strip()[0]
        dr = a["dr"] or Decimal("0"); cr = a["cr"] or Decimal("0")
        if head in ("4","7"):
            amt = cr - dr
            if amt:
                revenue.append({"code": code, "name": name, "amount": _fmt(amt)})
                tot_rev += amt
                famR[code[:famlen]] += amt
        elif head in ("5","6","8","9"):
            amt = dr - cr
            if amt:
                expense.append({"code": code, "name": name, "amount": _fmt(amt)})
                tot_exp += amt
                famE[code[:famlen]] += amt

    net = tot_rev - tot_exp
    rev_fam = [[k, _fmt(v)] for k, v in sorted(famR.items())]
    exp_fam = [[k, _fmt(v)] for k, v in sorted(famE.items())]

    fmt = (request.GET.get("format") or "").lower()
    if fmt == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{smart_str("income_statement.csv")}"'
        w = csv.writer(resp)
        w.writerow(["section","code","name","amount"])
        for r in revenue: w.writerow(["Revenue", r["code"], r["name"], r["amount"]])
        w.writerow(["Totals","","Total Revenue", _fmt(tot_rev)])
        for r in expense: w.writerow(["Expenses", r["code"], r["name"], r["amount"]])
        w.writerow(["Totals","","Total Expenses", _fmt(tot_exp)])
        w.writerow(["Totals","","Net Income", _fmt(net)])
        return resp
    if fmt == "xlsx":
        details = []
        for r in revenue: details.append(["Revenue", r["code"], r["name"], r["amount"]])
        details.append(["Totals","","Total Revenue", _fmt(tot_rev)])
        for r in expense: details.append(["Expenses", r["code"], r["name"], r["amount"]])
        details.append(["Totals","","Total Expenses", _fmt(tot_exp)])
        details.append(["Totals","","Net Income", _fmt(net)])
        extras = [
            ("Revenue Subtotals", ["family","amount"], rev_fam),
            ("Expenses Subtotals", ["family","amount"], exp_fam),
        ]
        return _xlsx_response("income_statement.xlsx", "Income Statement",
                              ["section","code","name","amount"], details, extras=extras)

    return render(request, "admin/accounting/reports/income_statement.html", {
        **admin.site.each_context(request),
        "title": "Income Statement",
        "date_from": df, "date_to": dt,
        "revenue": revenue, "expense": expense,
        "tot_rev": _fmt(tot_rev), "tot_exp": _fmt(tot_exp), "net_income": _fmt(net),
        "rev_fam": rev_fam, "exp_fam": exp_fam,
    })

def rc_dispatch(request, report_id):
    slug_to_name = {
        "trial-balance": "ledger_trial_balance",
        "general-ledger": "ledger_general_ledger",
        "balance-sheet": "ledger_balance_sheet",
        "income-statement": "ledger_income_statement",
    }
    name = slug_to_name.get(report_id)
    if not name:
        return HttpResponse(f"Report '{report_id}' not found.", status=404)
    url = reverse(name)
    q = request.META.get("QUERY_STRING")
    if q: url = f"{url}?{q}"
    return redirect(url)

def rc_compat(request, report_id):
    mapping = {
        "trial-balance": report_trial_balance,
        "general-ledger": report_general_ledger,
        "balance-sheet": report_balance_sheet,
        "income-statement": report_income_statement,
        "trial_balance": report_trial_balance,
        "general_ledger": report_general_ledger,
        "balance_sheet": report_balance_sheet,
        "income_statement": report_income_statement,
        "profit-and-loss": report_income_statement,
        "profit_and_loss": report_income_statement,
        "pnl": report_income_statement,
    }
    view = mapping.get(report_id)
    if view: return view(request)
    return rc_dispatch(request, report_id)

# ------------ routes ------------
urlpatterns = [
    path("admin/ledger/reportcenterproxy/trial-balance/",     admin.site.admin_view(report_trial_balance),    name="ledger_trial_balance"),
    path("admin/ledger/reportcenterproxy/general-ledger/",    admin.site.admin_view(report_general_ledger),   name="ledger_general_ledger"),
    path("admin/ledger/reportcenterproxy/balance-sheet/",     admin.site.admin_view(report_balance_sheet),    name="ledger_balance_sheet"),
    path("admin/ledger/reportcenterproxy/income-statement/",  admin.site.admin_view(report_income_statement), name="ledger_income_statement"),
    path("admin/ledger/reportcenterproxy/<slug:report_id>/",  rc_compat, name="report-center-proxy-compat"),
    path("admin/rc/<slug:report_id>/",                        rc_dispatch, name="report-center-proxy-rc"),
        path('admin/rcx/general-ledger.xlsx',    admin.site.admin_view(gl_xlsx), name='export_gl_xlsx'),
    path('admin/rcx/trial-balance.xlsx',     admin.site.admin_view(tb_xlsx), name='export_tb_xlsx'),
    path('admin/rcx/balance-sheet.xlsx',     admin.site.admin_view(bs_xlsx), name='export_bs_xlsx'),
    path('admin/rcx/income-statement.xlsx',  admin.site.admin_view(is_xlsx), name='export_is_xlsx'),
    path("admin/", admin.site.urls),
]

