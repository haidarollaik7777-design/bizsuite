from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional, List, Tuple

from django.apps import apps
from django.db import models
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce


def _first_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None


def _find_ledger_entry_model():
    """
    Heuristically pick the GL line model from the 'ledger' app:
    - must have numeric 'debit' and 'credit'
    - must have FK 'account'
    - must have a date-like field named 'date'
    Prefer classes whose name contains 'Entry'/'Line'/'Move'/'Ledger'.
    """
    try:
        cfg = apps.get_app_config("ledger")
    except Exception as e:
        raise LookupError("App 'ledger' not installed or not ready") from e

    candidates = []
    for m in cfg.get_models():
        f = m._meta.get_fields()
        names = {x.name: x for x in f if hasattr(x, "name")}
        # must-haves
        if "debit" not in names or "credit" not in names or "account" not in names or "date" not in names:
            continue
        # types
        if not isinstance(names["debit"], models.Field) or not isinstance(names["credit"], models.Field):
            continue
        # penalty/bonus scoring by name
        name_l = m.__name__.lower()
        score = 0
        for key in ("entry", "line", "move", "ledger"):
            if key in name_l:
                score += 1
        candidates.append((score, m))

    if not candidates:
        raise LookupError("Could not find a GL model in 'ledger' with fields: account, date, debit, credit.")

    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]


def _get_models():
    """
    Resolve models in your setup:
      - Company  -> common.Company
      - Account  -> ledger.Account
      - GL rows  -> best-match model discovered in ledger (see heuristic above)
    """
    Company = _first_model("common", "Company")
    if Company is None:
        raise LookupError("Missing model: common.Company")

    Account = _first_model("ledger", "Account")
    if Account is None:
        raise LookupError("Missing model: ledger.Account")

    LedgerEntry = _find_ledger_entry_model()
    return Company, Account, LedgerEntry


@dataclass(frozen=True)
class TBBucket:
    account_id: int
    account_code: str
    account_name: str
    type: str
    debit: Decimal
    credit: Decimal
    net: Decimal


def _sum_expr(field: str):
    return Coalesce(Sum(field), Value(0))


def general_ledger(
    *, company, account_ids: Optional[Iterable[int]] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None
):
    _, _, LedgerEntry = _get_models()
    qs = LedgerEntry.objects.filter(company=company)
    if account_ids:
        qs = qs.filter(account_id__in=list(account_ids))
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    # best-effort select_related if fields exist
    sr = []
    for rel in ("account", "voucher", "line"):
        try:
            LedgerEntry._meta.get_field(rel)
            sr.append(rel)
        except Exception:
            pass
    if sr:
        qs = qs.select_related(*sr)
    return qs.order_by("date", "id")


def trial_balance(
    *, company, date_from: Optional[date] = None, date_to: Optional[date] = None
) -> List[TBBucket]:
    _, Account, LedgerEntry = _get_models()
    qs = LedgerEntry.objects.filter(company=company)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    # figure account fields
    acct = Account._meta
    code_field = "code" if "code" in [f.name for f in acct.get_fields()] else "number"
    name_field = "name" if "name" in [f.name for f in acct.get_fields()] else "title"
    type_field = "type" if "type" in [f.name for f in acct.get_fields()] else "kind"

    rows = (
        qs.values("account_id", f"account__{code_field}", f"account__{name_field}", f"account__{type_field}")
          .annotate(debit=_sum_expr("debit"), credit=_sum_expr("credit"))
          .order_by(f"account__{code_field}")
    )

    out: List[TBBucket] = []
    for r in rows:
        dr = Decimal(r["debit"] or 0)
        cr = Decimal(r["credit"] or 0)
        out.append(
            TBBucket(
                account_id=r["account_id"],
                account_code=r[f"account__{code_field}"],
                account_name=r[f"account__{name_field}"],
                type=r[f"account__{type_field}"],
                debit=dr, credit=cr, net=dr - cr,
            )
        )
    return out


@dataclass(frozen=True)
class StatementLine:
    code: str
    name: str
    amount: Decimal


def profit_and_loss(
    *, company, date_from: date, date_to: date
) -> Tuple[List[StatementLine], Decimal]:
    tb = trial_balance(company=company, date_from=date_from, date_to=date_to)
    lines: List[StatementLine] = []
    total = Decimal("0")

    for b in tb:
        if b.type in ("I", "X"):  # Income / Expense
            amount = -b.net if b.type == "I" else b.net
            if amount:
                lines.append(StatementLine(code=b.account_code, name=b.account_name, amount=amount))
                total += amount
    return lines, total


def balance_sheet(
    *, company, as_of: date
) -> Tuple[List[StatementLine], Decimal]:
    tb = trial_balance(company=company, date_to=as_of)
    lines: List[StatementLine] = []
    check = Decimal("0")
    for b in tb:
        if b.type in ("A", "L", "E"):  # Asset / Liability / Equity
            amt = b.net
            if b.type in ("L", "E"):
                amt = -amt
            if amt:
                lines.append(StatementLine(code=b.account_code, name=b.account_name, amount=amt))
                check += amt
    return lines, check
