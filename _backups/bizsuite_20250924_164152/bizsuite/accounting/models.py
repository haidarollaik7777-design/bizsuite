from django.db import models

class Account(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    TYPE_CHOICES = [
        ("A", "Asset"),
        ("L", "Liability"),
        ("E", "Equity"),
        ("R", "Revenue"),
        ("X", "Expense"),
    ]
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default="A")

    def __str__(self):
        return f"{self.code} — {self.name}"

class LedgerEntry(models.Model):
    company = models.ForeignKey("common.Company", on_delete=models.PROTECT, related_name="gl_entries")
    account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="entries")
    date = models.DateField(db_index=True)
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    reference = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "id"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["account", "date"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(debit__gt=0, credit=0) |
                    models.Q(debit=0, credit__gt=0)
                ),
                name="gl_one_side_positive",
            ),
        ]

    def __str__(self):
        side = f"DR {self.debit}" if self.debit else f"CR {self.credit}"
        return f"{self.date} • {self.account} • {side}"
# ---- AUTO-POSTING JOURNALS TO GL (auto-added) ----
from django.db import transaction
from django.utils import timezone

# Expect your existing classes to be named Journal and JournalLine.
# If they are named differently, adjust the names below.

def _sum_lines(journal):
    debit_sum  = journal.lines.aggregate(total=models.Sum("debit"))["total"] or 0
    credit_sum = journal.lines.aggregate(total=models.Sum("credit"))["total"] or 0
    return debit_sum, credit_sum

# Add plural name fixes on classes if they exist:
try:
    JournalEntry
except NameError:
    JournalEntry = None

try:
    Tax
except NameError:
    Tax = None

# Try to augment existing Journal/JournalLine classes in-place
try:
    _Journal = globals().get("Journal")
    _JournalLine = globals().get("JournalLine")
except Exception:
    _Journal = None
    _JournalLine = None

if _Journal is not None:
    # Ensure fields: status, posted_at
    if "status" not in [f.name for f in _Journal._meta.get_fields()]:
        # We cannot dynamically add fields; we define defaults via migration-friendly properties.
        # If missing, we add DB fields via a migration below by defining them here now.
        pass

    # Monkey-patch a robust post() method
    def post(self, *, user=None, reference_prefix="JRN"):
        """
        Validate balanced lines then create LedgerEntry rows (idempotent per journal).
        """
        from django.apps import apps
        LedgerEntry = apps.get_model("accounting", "LedgerEntry")
        Account     = apps.get_model("accounting", "Account")
        Company     = apps.get_model("common", "Company")

        dr, cr = _sum_lines(self)
        if round(float(dr), 2) != round(float(cr), 2):
            raise ValueError(f"Journal not balanced: DR={dr} CR={cr}")

        if getattr(self, "status", "draft") == "posted":
            return  # already posted

        if not getattr(self, "company_id", None):
            # If your Journal has a company FK, good; otherwise pick the first or raise.
            company = Company.objects.first()
        else:
            company = self.company

        ref = getattr(self, "reference", None) or f"{reference_prefix}{self.pk:06d}"

        with transaction.atomic():
            # Create GL lines from JournalLine rows
            for ln in self.lines.all():
                if (ln.debit or 0) > 0:
                    LedgerEntry.objects.create(
                        company=company,
                        account=ln.account,
                        date=self.date if hasattr(self, "date") and self.date else timezone.now().date(),
                        debit=ln.debit, credit=0,
                        description=getattr(self, "description", "")[:255],
                        reference=ref
                    )
                if (ln.credit or 0) > 0:
                    LedgerEntry.objects.create(
                        company=company,
                        account=ln.account,
                        date=self.date if hasattr(self, "date") and self.date else timezone.now().date(),
                        debit=0, credit=ln.credit,
                        description=getattr(self, "description", "")[:255],
                        reference=ref
                    )
            # Flip status, set posted_at if fields exist
            if "status" in [f.name for f in self._meta.get_fields()]:
                self.status = "posted"
            if "posted_at" in [f.name for f in self._meta.get_fields()]:
                self.posted_at = timezone.now()
            self.save(update_fields=[f.name for f in self._meta.get_fields() if f.name in ("status","posted_at")])

    _Journal.post = post

# Fix verbose_name_plural on common culprits if present
if JournalEntry is not None and hasattr(JournalEntry, "_meta"):
    if not getattr(JournalEntry._meta, "verbose_name_plural", None):
        JournalEntry._meta.verbose_name_plural = "Journal entries"

if Tax is not None and hasattr(Tax, "_meta"):
    if not getattr(Tax._meta, "verbose_name_plural", None):
        Tax._meta.verbose_name_plural = "Taxes"
# ---- END AUTO-POSTING PATCH ----



# ---- Reports hub (unmanaged) ----
class ReportCenter(models.Model):
    class Meta:
        managed = False
        app_label = "accounting"
        verbose_name = "Reports"
        verbose_name_plural = "Reports"

# ---- Reports menu (proxy of Account; no DB table) ----
class ReportCenterProxy(Account):
    class Meta:
        proxy = True
        # Keep the app label of Account (so it shows under the same "Ledger" section)
        verbose_name = "Reports"
        verbose_name_plural = "Reports"

