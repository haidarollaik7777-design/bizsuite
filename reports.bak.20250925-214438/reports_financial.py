# reports/reports_financial.py
from datetime import date
from typing import Optional, Dict, Any, List, Tuple
from django.db.models import Sum
from django.utils.dateparse import parse_date

# Adjust these if your app label differs
from ledger.models import LedgerEntry, Account

# ----------------- Helpers -----------------
def _parse_dates(date_from: Optional[str], date_to: Optional[str]) -> Tuple[Optional[date], Optional[date]]:
    df = parse_date(date_from) if date_from else None
    dt = parse_date(date_to) if date_to else None
    return df, dt

def _pick_class_field() -> Optional[str]:
    # Try common field names that classify accounts
    candidates = ["type", "account_type", "category", "kind", "group", "class_name", "nature"]
    names = {f.name for f in Account._meta.get_fields() if hasattr(f, "name")}
    for c in candidates:
        if c in names:
            return c
    return None

def _logical_type(acc) -> Optional[str]:
    """Normalize the account type to one of: asset/liability/equity/revenue/expense."""
    fld = _pick_class_field()
    if fld:
        raw = getattr(acc, fld, None)
        if raw is not None:
            s = str(raw).strip().lower()
            mapv = {
                "assets":"asset","asset":"asset","1":"asset","a":"asset",
                "liabilities":"liability","liability":"liability","2":"liability","l":"liability",
                "equity":"equity","capital":"equity","owner equity":"equity","3":"equity","e":"equity",
                "revenue":"revenue","income":"revenue","sales":"revenue","sales revenue":"revenue","4":"revenue","7":"revenue","r":"revenue",
                "expense":"expense","expenses":"expense","operating expense":"expense","admin expense":"expense","selling expense":"expense",
                "purchases":"expense","purchase":"expense","cogs":"expense","cost of goods sold":"expense","cost of sales":"expense",
                "direct costs":"expense","indirect costs":"expense","5":"expense","6":"expense","8":"expense","9":"expense","x":"expense",
            }
            if s in mapv:
                return mapv[s]
    # fallback by code family
    code = getattr(acc, "code", None)
    if code:
        s = str(code).strip()
        if s:
            first = s[0]
            if first == "1": return "asset"
            if first == "2": return "liability"
            if first == "3": return "equity"
            if first in ("4","7"): return "revenue"
            if first in ("5","6","8","9"): return "expense"
    return None

def _sum(qs):
    return qs.aggregate(total=Sum("amount"))["total"] or 0

# ----------------- Reports -----------------
def build_trial_balance(date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    df, dt = _parse_dates(date_from, date_to)
    qs = LedgerEntry.objects.all()
    if df: qs = qs.filter(entry_date__gte=df)
    if dt: qs = qs.filter(entry_date__lte=dt)

    rows = []
    for acc in Account.objects.order_by("code"):
        acc_qs = qs.filter(account=acc)
        deb = _sum(acc_qs.filter(amount__gt=0))
        cre = abs(_sum(acc_qs.filter(amount__lt=0)))
        bal = deb - cre
        if deb or cre or bal:
            rows.append({
                "account_code": acc.code,
                "account_name": acc.name,
                "debit": float(deb),
                "credit": float(cre),
                "balance": float(bal),
            })
    return {
        "title": "Trial Balance",
        "columns": ["account_code","account_name","debit","credit","balance"],
        "rows": rows, "date_from": df, "date_to": dt,
    }

def build_general_ledger(date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    df, dt = _parse_dates(date_from, date_to)
    qs = LedgerEntry.objects.select_related("account").order_by("entry_date","id")
    if df: qs = qs.filter(entry_date__gte=df)
    if dt: qs = qs.filter(entry_date__lte=dt)

    rows = []
    for le in qs:
        amt = float(le.amount or 0)
        rows.append({
            "date": le.entry_date.isoformat(),
            "account_code": le.account.code,
            "account_name": le.account.name,
            "debit": amt if amt > 0 else 0.0,
            "credit": abs(amt) if amt < 0 else 0.0,
            "memo": le.memo or "",
            "doc_no": getattr(le, "doc_no", "") or "",
        })
    return {
        "title": "General Ledger",
        "columns": ["date","account_code","account_name","debit","credit","memo","doc_no"],
        "rows": rows, "date_from": df, "date_to": dt,
    }

def build_balance_sheet(date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    # Snapshot at date_to
    _, dt = _parse_dates(date_from, date_to)
    qs = LedgerEntry.objects.select_related("account")
    if dt: qs = qs.filter(entry_date__lte=dt)

    rows: List[Dict[str, Any]] = []
    totals = {"asset": 0.0, "liability": 0.0, "equity": 0.0}

    # A/L/E
    for acc in Account.objects.order_by("code"):
        t = _logical_type(acc)
        if t not in ("asset","liability","equity"):
            continue
        s = _sum(qs.filter(account=acc))
        val = float(s if t == "asset" else -s)  # invert credit-nature
        if val != 0:
            rows.append({"section": "Assets" if t=="asset" else ("Liabilities" if t=="liability" else "Equity"),
                         "account_code": acc.code, "account_name": acc.name, "amount": val})
            totals[t] += val

    # Earnings to date (Revenue - Expenses) → Equity
    rev_total = 0.0
    exp_total = 0.0
    for acc in Account.objects.order_by("code"):
        t = _logical_type(acc)
        if t == "revenue":
            s = _sum(qs.filter(account=acc))
            rev_total += float(-s)  # show positive
        elif t == "expense":
            s = _sum(qs.filter(account=acc))
            exp_total += float(s)
    net = rev_total - exp_total
    if net != 0:
        rows.append({"section": "Equity", "account_code": "", "account_name": "Retained Earnings (to date)", "amount": net})
        totals["equity"] += net

    rows.append({"section": "Totals", "account_code": "", "account_name": "Total Assets", "amount": totals["asset"]})
    rows.append({"section": "Totals", "account_code": "", "account_name": "Total Liabilities + Equity", "amount": totals["liability"] + totals["equity"]})

    return {
        "title": "Balance Sheet",
        "columns": ["section","account_code","account_name","amount"],
        "rows": rows, "date_from": None, "date_to": dt,
    }

def build_income_statement(date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    df, dt = _parse_dates(date_from, date_to)
    qs = LedgerEntry.objects.select_related("account")
    if df: qs = qs.filter(entry_date__gte=df)
    if dt: qs = qs.filter(entry_date__lte=dt)

    rows: List[Dict[str, Any]] = []
    rev_total = 0.0
    exp_total = 0.0

    for acc in Account.objects.order_by("code"):
        t = _logical_type(acc)
        if t == "revenue":
            s = _sum(qs.filter(account=acc))
            v = float(-s)   # credit-nature → positive
            if v: rows.append({"section":"Revenue","account_code":acc.code,"account_name":acc.name,"amount":v})
            rev_total += v
        elif t == "expense":
            s = _sum(qs.filter(account=acc))
            v = float(s)    # debit-nature
            if v: rows.append({"section":"Expense","account_code":acc.code,"account_name":acc.name,"amount":v})
            exp_total += v

    net = rev_total - exp_total
    rows.append({"section":"Totals","account_code":"","account_name":"Total Revenue","amount":rev_total})
    rows.append({"section":"Totals","account_code":"","account_name":"Total Expenses","amount":exp_total})
    rows.append({"section":"Totals","account_code":"","account_name":"Net Income","amount":net})

    return {
        "title": "Income Statement",
        "columns": ["section","account_code","account_name","amount"],
        "rows": rows, "date_from": df, "date_to": dt,
    }
