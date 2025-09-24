from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from core.models import Company
from accounting.query import trial_balance

class Command(BaseCommand):
    help = "Export Trial Balance: manage.py trial_balance <company_id> [--from YYYY-MM-DD] [--to YYYY-MM-DD]"

    def add_arguments(self, parser):
        parser.add_argument("company_id", type=int)
        parser.add_argument("--from", dest="date_from")
        parser.add_argument("--to", dest="date_to")

    def handle(self, *args, **opts):
        try:
            co = Company.objects.get(id=opts["company_id"])
        except Company.DoesNotExist:
            raise CommandError("Company not found")

        date_from = datetime.fromisoformat(opts["date_from"]).date() if opts.get("date_from") else None
        date_to   = datetime.fromisoformat(opts["date_to"]).date() if opts.get("date_to") else None

        buckets = trial_balance(company=co, date_from=date_from, date_to=date_to)

        self.stdout.write("code,name,type,debit,credit,net")
        total_dr = Decimal("0"); total_cr = Decimal("0")
        for b in buckets:
            self.stdout.write(f"{b.account_code},{b.account_name},{b.type},{b.debit:.2f},{b.credit:.2f},{b.net:.2f}")
            total_dr += b.debit; total_cr += b.credit
        self.stdout.write(f"TOTAL,,,{total_dr:.2f},{total_cr:.2f},{(total_dr-total_cr):.2f}")
