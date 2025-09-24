from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from .models import WorkOrder

@shared_task
def send_due_workorders(days_ahead=3, to="ops@localhost"):
    now = timezone.now().date()
    cutoff = now + timezone.timedelta(days=days_ahead)
    qs = WorkOrder.objects.filter(status__in=["OPEN","IN_PROGRESS"], due_date__isnull=False, due_date__lte=cutoff).order_by("due_date","priority")
    rows = []
    for w in qs:
        rows.append(f"- WO#{w.pk} [{w.priority}] {w.title} (Asset: {w.asset.code}) due {w.due_date} — {w.status}")
    if not rows:
        body = f"No due work orders in next {days_ahead} day(s)."
    else:
        body = "Work orders due soon:\n" + "\n".join(rows)

    msg = EmailMessage(
        subject=f"Maintenance – Work Orders due in {days_ahead} day(s)",
        body=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "erp@localhost"),
        to=[to]
    )
    msg.send()
    return {"count": qs.count(), "to": to, "cutoff": str(cutoff)}
