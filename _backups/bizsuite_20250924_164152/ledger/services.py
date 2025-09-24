from decimal import Decimal
from django.db import transaction
from .models import Invoice, JournalEntry, JournalLine, Account

@transaction.atomic
def post_invoice(invoice: Invoice, ar_account: Account, revenue_or_expense_account: Account):
    if invoice.posted: return invoice
    je = JournalEntry.objects.create(company=invoice.company, date=invoice.date, ref=f"INV{invoice.id}")
    total = Decimal("0.00")
    for line in invoice.lines.all():
        line_total = (line.quantity * line.unit_price).quantize(Decimal("0.01"))
        total += line_total
        JournalLine.objects.create(entry=je, account=revenue_or_expense_account,
            credit=line_total if invoice.type==Invoice.OUT else Decimal("0.00"),
            debit=line_total if invoice.type==Invoice.IN_ else Decimal("0.00"),
            label=line.product_name)
    JournalLine.objects.create(entry=je, account=ar_account,
        debit=total if invoice.type==Invoice.OUT else Decimal("0.00"),
        credit=total if invoice.type==Invoice.IN_ else Decimal("0.00"),
        label="Counterparty")
    invoice.posted = True
    invoice.save(update_fields=["posted"])
    return invoice
