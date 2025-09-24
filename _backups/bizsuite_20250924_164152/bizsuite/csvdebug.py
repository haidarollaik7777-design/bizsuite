from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import csv
from typing import Optional
from importlib import import_module

from django.apps import apps
from django.db import transaction

def _parse_date(d: Optional[str|date]) -> Optional[date]:
    if not d:
        return None
    if isinstance(d, date):
        return d
    return datetime.fromisoformat(str(d)).date()

@transaction.atomic
def tb_auto_csv(company_id: int, date_from: Optional[str|date] = None,
                date_to: Optional[str|date] = None, out_path: Optional[str|Path] = None) -> str:
    # Resolve models/modules lazily
    Company = apps.get_model("common","Company")
    query = import_module("accounting.query")

    date_from = _parse_date(date_from)
    date_to   = _parse_date(date_to)

    co = Company.objects.get(id=company_id)
    buckets = query.trial_balance(company=co, date_from=date_from, date_to=date_to)

    if not out_path:
        tag_from = date_from.isoformat() if date_from else "begin"
        tag_to   = date_to.isoformat()   if date_to   else "today"
        out_path = Path(f"tb_{co.id}_{tag_from}_to_{tag_to}.csv")
    out_path = Path(out_path)

    total_dr = Decimal("0"); total_cr = Decimal("0")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code","name","type","debit","credit","net"])
        for b in buckets:
            w.writerow([b.account_code, b.account_name, b.type, f"{b.debit:.2f}", f"{b.credit:.2f}", f"{b.net:.2f}"])
            total_dr += b.debit; total_cr += b.credit
        w.writerow(["TOTAL","","", f"{total_dr:.2f}", f"{total_cr:.2f}", f"{(total_dr-total_cr):.2f}"])
    return str(out_path)

