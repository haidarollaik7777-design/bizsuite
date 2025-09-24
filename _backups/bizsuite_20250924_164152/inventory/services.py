from decimal import Decimal
from django.db import transaction
from .models import StockMove, StockLot

@transaction.atomic
def receive(product, warehouse, qty, unit_cost, date, company=None, ref=""):
    move = StockMove.objects.create(company=company or product.company, product=product, warehouse=warehouse, type="IN", quantity=qty, unit_cost=unit_cost, date=date, ref=ref)
    StockLot.objects.create(company=company or product.company, product=product, warehouse=warehouse, quantity_remaining=qty, unit_cost=unit_cost)
    return move

@transaction.atomic
def ship(product, warehouse, qty, date, company=None, ref=""):
    remaining = Decimal(qty)
    cost_total = Decimal("0.00")
    lots = StockLot.objects.select_for_update().filter(product=product, warehouse=warehouse).order_by('created_at')
    for lot in lots:
        if remaining <= 0: break
        take = min(remaining, lot.quantity_remaining)
        if take > 0:
            lot.quantity_remaining -= take
            lot.save(update_fields=["quantity_remaining"])
            cost_total += take * lot.unit_cost
            remaining -= take
    avg_cost = (cost_total/Decimal(qty)) if Decimal(qty) else Decimal("0.00")
    move = StockMove.objects.create(company=company or product.company, product=product, warehouse=warehouse, type="OUT", quantity=qty, unit_cost=avg_cost, date=date, ref=ref)
    return move, cost_total
