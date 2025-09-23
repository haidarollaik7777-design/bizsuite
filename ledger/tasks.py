from celery import shared_task
from django.utils import timezone

@shared_task
def daily_backup_marker():
    print(f"[{timezone.now()}] Daily backup marker ran")
    return "ok"
