from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator
from common.models import TimeStampedModel, Company, Partner

class Account(TimeStampedModel):
    TYPES = [(t,t) for t in ["ASSET","LIABILITY","EQUITY","INCOME","EXPENSE"]]
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=TYPES)
    is_reconcilable = models.BooleanField(default=False)
    class Meta: unique_together = ("company","code")

class Journal(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

class JournalEntry(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT, null=True, blank=True)
    date = models.DateField()
    ref = models.CharField(max_length=50, blank=True)

class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, related_name="lines", on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    partner = models.ForeignKey(Partner, null=True, blank=True, on_delete=models.SET_NULL)
    label = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])

class Tax(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=5, decimal_places=2)

class Invoice(TimeStampedModel):
    OUT, IN_ = ("OUT","IN")
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT)
    type = models.CharField(max_length=3, choices=[(OUT,"OUT"),(IN_,"IN")])
    date = models.DateField()
    posted = models.BooleanField(default=False)

class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="lines", on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_price = models.DecimalField(max_digits=14, decimal_places=4)
# ---- Reports menu (proxy of Account; no DB table) ----
class ReportCenterProxy(Account):
    class Meta:
        proxy = True
        app_label = "ledger"       # show under the Ledger section
        verbose_name = "Reports"
        verbose_name_plural = "Reports"
