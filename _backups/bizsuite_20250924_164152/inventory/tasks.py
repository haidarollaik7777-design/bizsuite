import os
from datetime import date, timedelta
from celery import shared_task
from django.conf import settings

def _recipients():
    raw = os.getenv("ALERTS_TO", "")
    return [e.strip() for e in raw.split(",") if e.strip()]

@shared_task
def send_min_stock_alerts():
    from inventory.models import Product
    alerts = []
    # If your Product has a cached on-hand, use it; otherwise sum lots.
    for p in Product.objects.all():
        rp = getattr(p, "reorder_point", None)
        if rp is None:
            continue
        qty = getattr(p, "quantity_on_hand", None)
        if qty is None and hasattr(p, "stocklot_set"):
            qty = sum(getattr(l, "quantity_remaining", 0) for l in p.stocklot_set.all())
        try:
            qf, rf = float(qty or 0), float(rp)
        except Exception:
            continue
        if qf <= rf:
            sku = getattr(p, "sku", None) or getattr(p, "id", None)
            alerts.append(f"{sku} — On hand {qf} <= Reorder {rf}")
    if alerts and _recipients():
        from django.core.mail import send_mail
        send_mail(
            subject="BizSuite: Minimum stock alerts",
            message="\n".join(alerts),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
            recipient_list=_recipients(),
        )
    return {"count": len(alerts)}

@shared_task
def send_expiry_alerts(days_ahead=30):
    from inventory.models import StockLot
    alerts = []
    today = date.today()
    horizon = today + timedelta(days=int(days_ahead))
    if not hasattr(StockLot, "expiry_date"):
        return {"count": 0}
    lots = StockLot.objects.filter(expiry_date__isnull=False, expiry_date__lte=horizon)
    for lot in lots:
        prod = getattr(lot, "product", None)
        sku = getattr(prod, "sku", None) or getattr(prod, "id", None)
        qrem = getattr(lot, "quantity_remaining", 0)
        alerts.append(f"{sku} lot#{lot.id} expires {lot.expiry_date} (qty {qrem})")
    if alerts and _recipients():
        from django.core.mail import send_mail
        send_mail(
            subject=f"BizSuite: Lots expiring in ≤{days_ahead} days",
            message="\n".join(alerts),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
            recipient_list=_recipients(),
        )
    return {"count": len(alerts)}