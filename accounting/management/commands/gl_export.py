from __future__ import annotations
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from core.models import Company
from accounting.models import Account
from accounting.query import general_ledger

class Command(BaseCommand):
    help = "Export GL: manage.py gl_export <company_id> [--accounts 1000,4000] [--from YYYY-MM-DD] [--to YYYY-MM-DD]"

    def add_arguments(self, parser):
        parser.add_argument("company_id", type=int)
        parser.add_argument("--accounts", type=str)
        parser.add_argument("--from", dest="date_from")
        parser.add_argument("--to", dest="date_to")

    def handle(self, *args, **opts):
        try:
            co = Company.objects.get(id=opts["company_id"])
        except Company.DoesNotExist:
            raise CommandError("Company not found")

        acct_ids = None
        if opts.get("accounts"):
            codes = [c.strip() for c in opts["accounts"].split(",") if c.strip()]
            acct_ids = list(Account.objects.filter(company=co, code__in=codes).values_list("id", flat=True))
            if not acct_ids:
                raise CommandError("No matching accounts")

        date_from = datetime.fromisoformat(opts["date_from"]).date() if opts.get("date_from") else None
        date_to   = datetime.fromisoformat(opts["date_to"]).date() if opts.get("date_to") else None

        qs = general_ledger(company=co, account_ids=acct_ids, date_from=date_from, date_to=date_to)

        self.stdout.write("date,voucher,account,desc,debit,credit")
        for e in qs:
            self.stdout.write(f"{e.date},{e.voucher.journal.code}-{e.voucher.number},{e.account.code},{e.line.description},{e.debit:.2f},{e.credit:.2f}")
