from __future__ import annotations
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from core.models import Company
from accounting.query import balance_sheet

class Command(BaseCommand):
    help = "Balance Sheet: manage.py balance_sheet <company_id> --as YYYY-MM-DD"

    def add_arguments(self, parser):
        parser.add_argument("company_id", type=int)
        parser.add_argument("--as", dest="as_of", required=True)

    def handle(self, *args, **opts):
        try:
            co = Company.objects.get(id=opts["company_id"])
        except Company.DoesNotExist:
            raise CommandError("Company not found")

        as_of = datetime.fromisoformat(opts["as_of"]).date()

        lines, check = balance_sheet(company=co, as_of=as_of)
        self.stdout.write("code,name,amount")
        for ln in lines:
            self.stdout.write(f"{ln.code},{ln.name},{ln.amount:.2f}")
        self.stdout.write(f"CHECK_SUM,{check:.2f}")
