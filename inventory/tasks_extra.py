from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone

@shared_task
def send_inventory_test_email(to="test@inbox.local"):
    subject = f"Inventory Alerts TEST (Celery) {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    body = "This is a Celery-sent test from BizSuite inventory."
    EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [to]).send()
    return {"to": to, "ok": True}
