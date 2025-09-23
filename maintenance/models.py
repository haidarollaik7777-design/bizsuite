from django.db import models
from django.utils import timezone

class Asset(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        RETIRED = "RETIRED", "Retired"

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=64, unique=True)
    category = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    serial_number = models.CharField(max_length=200, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    vendor = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    next_pm_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.code} - {self.name}"

class WorkOrder(models.Model):
    class Priority(models.TextChoices):
        LOW="LOW","Low"; MEDIUM="MEDIUM","Medium"; HIGH="HIGH","High"; CRITICAL="CRITICAL","Critical"
    class Status(models.TextChoices):
        OPEN="OPEN","Open"; IN_PROGRESS="IN_PROGRESS","In Progress"; DONE="DONE","Done"; CANCELLED="CANCELLED","Cancelled"

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="workorders")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    due_date = models.DateField(null=True, blank=True)
    assigned_to = models.CharField(max_length=200, blank=True)  # simple text owner
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self): return f"WO#{self.pk} {self.title}"

class MaintenanceSchedule(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="schedules")
    frequency_days = models.PositiveIntegerField(default=90)
    last_done = models.DateField(null=True, blank=True)
    next_due = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def compute_next_due(self):
        base = self.last_done or timezone.now().date()
        return base + timezone.timedelta(days=self.frequency_days)

    def save(self, *args, **kwargs):
        if not self.next_due:
            self.next_due = self.compute_next_due()
        super().save(*args, **kwargs)
