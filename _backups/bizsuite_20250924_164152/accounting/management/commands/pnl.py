from __future__ import annotations
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from core.models import Company
from accounting.query import profit_and_loss

class Command(BaseCommand):
    help = "P&L: manage.py pnl <company_id> --from YYYY-MM-DD --to YYYY-MM-DD"

    def add_arguments(self, parser):
        parser.add_argument("company_id", type=int)
        parser.add_argument("--from", dest="date_from", required=True)
        parser.add_argument("--to", dest="date_to", required=True)

    def handle(self, *args, **opts):
        try:
            co = Company.objects.get(id=opts["company_id"])
        except Company.DoesNotExist:
            raise CommandError("Company not found")

        date_from = datetime.fromisoformat(opts["date_from"]).date()
        date_to   = datetime.fromisoformat(opts["date_to"]).date()

        lines, total = profit_and_loss(company=co, date_from=date_from, date_to=date_to)
        self.stdout.write("code,name,amount")
        for ln in lines:
            self.stdout.write(f"{ln.code},{ln.name},{ln.amount:.2f}")
        self.stdout.write(f"TOTAL_PROFIT,{total:.2f}")
