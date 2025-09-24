from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from common.models import Company
from accounting.models import Account, Journal
from accounting.services import LineInput, create_and_post

class Command(BaseCommand):
    help = "Generate demo company, COA, a few vouchers and post them."

    def handle(self, *args, **opts):
        u, _ = User.objects.get_or_create(username="demo")
        co, _ = Company.objects.get_or_create(name="Bizsuite Demo", defaults={"base_currency": "USD"})
        gj, _ = Journal.objects.get_or_create(company=co, code="GJ", defaults={"name": "General Journal"})
        cash, _ = Account.objects.get_or_create(company=co, code="1000", defaults={"name": "Cash", "type": Account.Type.ASSET})
        ar,   _ = Account.objects.get_or_create(company=co, code="1100", defaults={"name": "Accounts Receivable", "type": Account.Type.ASSET})
        ap,   _ = Account.objects.get_or_create(company=co, code="2100", defaults={"name": "Accounts Payable", "type": Account.Type.LIABILITY})
        cap,  _ = Account.objects.get_or_create(company=co, code="3100", defaults={"name": "Capital", "type": Account.Type.EQUITY})
        rev,  _ = Account.objects.get_or_create(company=co, code="4000", defaults={"name": "Revenue", "type": Account.Type.INCOME})
        exp,  _ = Account.objects.get_or_create(company=co, code="5000", defaults={"name": "Expense", "type": Account.Type.EXPENSE})
        today = date.today(); d1, d2, d3 = today - timedelta(days=5), today - timedelta(days=3), today
        create_and_post(company=co, journal=gj, number="JV-0001", date=d1,
                        lines=[LineInput(account_id=cash.id, debit=Decimal("5000.00")),
                               LineInput(account_id=cap.id,  credit=Decimal("5000.00"))],
                        created_by=u, posted_by=u)
        create_and_post(company=co, journal=gj, number="JV-0002", date=d2,
                        lines=[LineInput(account_id=ar.id,  debit=Decimal("1500.00")),
                               LineInput(account_id=rev.id, credit=Decimal("1500.00"))],
                        created_by=u, posted_by=u)
        create_and_post(company=co, journal=gj, number="JV-0003", date=d3,
                        lines=[LineInput(account_id=exp.id,  debit=Decimal("300.00")),
                               LineInput(account_id=cash.id, credit=Decimal("300.00"))],
                        created_by=u, posted_by=u)
        self.stdout.write(self.style.SUCCESS("Demo data generated and posted."))

