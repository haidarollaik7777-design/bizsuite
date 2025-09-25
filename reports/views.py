from urllib.parse import parse_qsl, urlencode
from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import Http404

from .utils.csv_export import rows_to_csv_response, safe_date
from .utils.xlsx_export import rows_to_xlsx_response

# -------- helpers: format toggles + dates --------
def _is_csv(request):   return (request.GET.get("format") or "").lower() == "csv"
def _want_xlsx(request):return (request.GET.get("format") or "").lower() in ("xlsx","excel")

def _date_range(request):
    today = timezone.now().date()
    dfrom = request.GET.get("from")
    dto   = request.GET.get("to")
    if not dfrom and not dto:
        import calendar
        dfrom = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        dto = today.replace(day=last_day)
    else:
        dfrom = safe_date(dfrom, today.replace(day=1))
        dto   = safe_date(dto, today)
    return dfrom, dto

# -------- helpers: model detection (robust across schemas) --------
def _get_JournalLine():
    from django.apps import apps as djapps
    candidates = [
        ("accounting", "JournalLine"),
        ("ledger",     "JournalLine"),
        ("accounting", "JournalEntryLine"),
        ("ledger",     "JournalEntryLine"),
        ("finance",    "JournalLine"),
    ]
    for app_label, model_name in candidates:
        try:
            M = djapps.get_model(app_label, model_name)
            if M:
                return M
        except Exception:
            pass
    raise LookupError("Could not find a Journal Line model. Tried: " + ", ".join([f"{a}.{m}" for a,m in candidates]))

def _detect_entry_relation_and_fields(JournalLine):
    # Return (entry_fk_name, EntryModel)
    for nm in ("entry","journal_entry","move","voucher","document"):
        try:
            f = JournalLine._meta.get_field(nm)
            if getattr(f, "is_relation", False):
                return f.name, f.related_model
        except Exception:
            pass
    for f in JournalLine._meta.get_fields():
        if getattr(f,"is_relation",False) and getattr(f,"many_to_one",False):
            rm = getattr(f,"related_model",None)
            if rm:
                title = (rm.__name__ + " " + getattr(getattr(rm,"_meta",None),"verbose_name","")).lower()
                if "entry" in title or "journal" in title:
                    return f.name, rm
    for f in JournalLine._meta.get_fields():
        if getattr(f,"is_relation",False) and getattr(f,"many_to_one",False):
            return f.name, f.related_model
    return None, None

def _build_entry_filters(entry_fk, EntryModel, dfrom, dto):
    filters = {}
    if not entry_fk or not EntryModel:
        return filters
    # date field
    from django.db.models import DateField, DateTimeField
    date_name = None
    for nm in ("date","posting_date","entry_date","txn_date","transaction_date","posted_on","created","created_at"):
        try:
            f = EntryModel._meta.get_field(nm)
            if isinstance(f,(DateField,DateTimeField)):
                date_name = nm; break
        except Exception:
            pass
    if not date_name:
        for f in EntryModel._meta.get_fields():
            try:
                if isinstance(f,(DateField,DateTimeField)):
                    date_name = f.name; break
            except Exception:
                pass
    if date_name:
        filters[f"{entry_fk}__{date_name}__gte"] = dfrom
        filters[f"{entry_fk}__{date_name}__lte"] = dto
    # posted boolean (optional)
    for nm in ("is_posted","posted","is_finalized","is_approved","posted_flag"):
        try:
            f = EntryModel._meta.get_field(nm)
            if getattr(f,"get_internal_type",lambda:"")() == "BooleanField":
                filters[f"{entry_fk}__{nm}"] = True; break
        except Exception:
            pass
    return filters

def _detect_account_relation_and_fields(JournalLine):
    # Return (acct_fk, AccountModel, code_field, name_field)
    acct_fk = AccountModel = code_field = name_field = None
    for nm in ("account","acct","ledger_account","gl_account","account_ref"):
        try:
            f = JournalLine._meta.get_field(nm)
            if getattr(f,"is_relation",False) and getattr(f,"many_to_one",False):
                acct_fk, AccountModel = f.name, f.related_model; break
        except Exception:
            pass
    if not acct_fk:
        for f in JournalLine._meta.get_fields():
            if getattr(f,"is_relation",False) and getattr(f,"many_to_one",False):
                rm = getattr(f,"related_model",None)
                if rm:
                    title = (rm.__name__ + " " + getattr(getattr(rm,"_meta",None),"verbose_name","")).lower()
                    if "account" in title or "ledger" in title:
                        acct_fk, AccountModel = f.name, rm; break
    if not acct_fk:
        for f in JournalLine._meta.get_fields():
            if getattr(f,"is_relation",False) and getattr(f,"many_to_one",False):
                acct_fk, AccountModel = f.name, f.related_model; break

    def has_field(model, fname):
        try:
            model._meta.get_field(fname); return True
        except Exception:
            return False

    for nm in ("code","number","no","account_code","acct_code","id_code"):
        if AccountModel and has_field(AccountModel, nm):
            code_field = nm; break
    for nm in ("name","title","account_name","description","label"):
        if AccountModel and has_field(AccountModel, nm):
            name_field = nm; break
    if not code_field and AccountModel:
        for f in AccountModel._meta.get_fields():
            if getattr(f,"get_internal_type",lambda:"")() in ("CharField","TextField"):
                code_field = f.name; break
    if not name_field:
        name_field = code_field or "id"
    return acct_fk, AccountModel, code_field, name_field

# ---------- Proxy redirect (admin/ledger/reportcenterproxy/<slug>/ → /admin/reports/<slug>/...) ----------
def report_center_proxy(request, report_id: str):
    mapping = {
        "trial-balance":   "/admin/reports/trial-balance/",
        "general-ledger":  "/admin/reports/general-ledger/",
        "income-statement":"/admin/reports/income-statement/",
        "balance-sheet":   "/admin/reports/balance-sheet/",  # future
    }
    target = mapping.get(report_id, "/admin/reports/")
    qs = request.META.get("QUERY_STRING","")
    if qs: target = f"{target}?{qs}"
    return redirect(target)

# =================================
# Reports (uniform CSV / XLSX / HTML)
# =================================

def report_general_ledger(request):
    dfrom, dto = _date_range(request)
    JournalLine = _get_JournalLine()
    entry_fk, EntryModel = _detect_entry_relation_and_fields(JournalLine)
    acct_fk, AccountModel, code_field, name_field = _detect_account_relation_and_fields(JournalLine)

    code_prefix = (request.GET.get("code_prefix") or "").strip()

    # Build queryset with safe filters
    q = JournalLine.objects.all()
    ef = _build_entry_filters(entry_fk, EntryModel, dfrom, dto)
    if ef: q = q.filter(**ef)
    if code_prefix and acct_fk and code_field:
        q = q.filter(**{f"{acct_fk}__{code_field}__startswith": code_prefix})

    # Resolve date attribute for display
    entry_date_attr = None
    if entry_fk and EntryModel:
        for nm in ("date","posting_date","entry_date","txn_date","transaction_date","posted_on","created","created_at"):
            try:
                EntryModel._meta.get_field(nm); entry_date_attr = nm; break
            except Exception: pass

    # Materialize display/export rows to avoid template touching model fields
    rows = []
    for ln in q.order_by("id"):
        # date
        dstr = ""
        if entry_fk and entry_date_attr:
            try:
                eobj = getattr(ln, entry_fk, None)
                dval = getattr(eobj, entry_date_attr, None)
                dstr = dval.isoformat() if dval else ""
            except Exception:
                pass
        # account code/name
        code = name = ""
        try:
            aobj = getattr(ln, acct_fk) if acct_fk else None
            code = getattr(aobj, code_field) if (aobj and code_field) else ""
            name = getattr(aobj, name_field) if (aobj and name_field) else ""
        except Exception:
            pass
        debit  = float(getattr(ln,"debit",0)  or 0)
        credit = float(getattr(ln,"credit",0) or 0)
        memo   = (getattr(ln,"memo",None) or getattr(getattr(ln, entry_fk, None),"memo",None) or "")
        rows.append([dstr, str(code), str(name), f"{debit:.2f}", f"{credit:.2f}", str(memo)[:500]])

    headers = ["Date","Code","Name","Debit","Credit","Memo"]
    if _is_csv(request):
        return rows_to_csv_response(f"general_ledger_{dfrom}_to_{dto}", headers, rows)
    if _want_xlsx(request):
        return rows_to_xlsx_response(f"general_ledger_{dfrom}_to_{dto}", headers, rows)

    return render(request, "admin/accounting/reports/general_ledger.html", {
        "dfrom": dfrom, "dto": dto, "code_prefix": code_prefix, "rows": rows
    })

def report_trial_balance(request):
    from django.db.models import Sum, Value
    from django.db.models.functions import Coalesce

    dfrom, dto = _date_range(request)
    JournalLine = _get_JournalLine()
    entry_fk, EntryModel = _detect_entry_relation_and_fields(JournalLine)
    acct_fk, AccountModel, code_field, name_field = _detect_account_relation_and_fields(JournalLine)

    code_prefix = (request.GET.get("code_prefix") or "").strip()

    q = JournalLine.objects.all()
    ef = _build_entry_filters(entry_fk, EntryModel, dfrom, dto)
    if ef: q = q.filter(**ef)
    if code_prefix and acct_fk and code_field:
        q = q.filter(**{f"{acct_fk}__{code_field}__startswith": code_prefix})

    vals = []
    if acct_fk and code_field: vals.append(f"{acct_fk}__{code_field}")
    if acct_fk and name_field: vals.append(f"{acct_fk}__{name_field}")
    if not vals: vals = ["id"]

    period = (q.values(*([f"{acct_fk}_id"] if acct_fk else ["id"]), *vals)
                .annotate(deb=Coalesce(Sum("debit"), Value(0)),
                          cre=Coalesce(Sum("credit"), Value(0)))
                .order_by(*vals))

    rows = []
    total_deb = total_cre = 0.0
    for r in period:
        deb = float(r["deb"] or 0.0); cre = float(r["cre"] or 0.0)
        total_deb += deb; total_cre += cre
        c = r.get(f"{acct_fk}__{code_field}", "") if acct_fk and code_field else ""
        n = r.get(f"{acct_fk}__{name_field}", "") if acct_fk and name_field else ""
        rows.append([c, n, f"{deb:.2f}", f"{cre:.2f}", f"{(deb-cre):.2f}"])

    headers = ["Code","Name","Debit","Credit","Balance"]
    if _is_csv(request):
        rows.append(["TOTALS","", f"{total_deb:.2f}", f"{total_cre:.2f}", f"{(total_deb-total_cre):.2f}"])
        return rows_to_csv_response(f"trial_balance_{dfrom}_to_{dto}", headers, rows)
    if _want_xlsx(request):
        rows.append(["TOTALS","", f"{total_deb:.2f}", f"{total_cre:.2f}", f"{(total_deb-total_cre):.2f}"])
        return rows_to_xlsx_response(f"trial_balance_{dfrom}_to_{dto}", headers, rows)

    return render(request, "admin/accounting/reports/trial_balance.html", {
        "dfrom": dfrom, "dto": dto, "code_prefix": code_prefix,
        "rows": rows, "total_deb": total_deb, "total_cre": total_cre,
        "balanced": abs(total_deb-total_cre) < 0.005
    })

def report_income_statement(request):
    from django.db.models import Sum, Value
    from django.db.models.functions import Coalesce

    dfrom, dto = _date_range(request)
    JournalLine = _get_JournalLine()
    entry_fk, EntryModel = _detect_entry_relation_and_fields(JournalLine)
    acct_fk, AccountModel, code_field, name_field = _detect_account_relation_and_fields(JournalLine)

    code_prefix = (request.GET.get("code_prefix") or "").strip()

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
        deb = float(r["deb"] or 0.0); cre = float(r["cre"] or 0.0)

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
    rows = []
    rows.append(["Revenue","",""])
    rows += (revenue_rows or [["(No rows)","","0.00"]])
    rows.append(["Total Revenue","","{:.2f}".format(total_rev)])
    rows.append(["Expenses","",""])
    rows += (expense_rows or [["(No rows)","","0.00"]])
    rows.append(["Total Expenses","","{:.2f}".format(total_exp)])
    rows.append(["Net Income","","{:.2f}".format(net_income)])

    if _is_csv(request):
        return rows_to_csv_response(f"income_statement_{dfrom}_to_{dto}", headers, rows)
    if _want_xlsx(request):
        return rows_to_xlsx_response(f"income_statement_{dfrom}_to_{dto}", headers, rows)

    return render(request, "admin/accounting/reports/income_statement.html", {
        "dfrom": dfrom, "dto": dto, "code_prefix": code_prefix,
        "revenue_rows": revenue_rows, "expense_rows": expense_rows,
        "total_rev": total_rev, "total_exp": total_exp, "net_income": net_income
    })
