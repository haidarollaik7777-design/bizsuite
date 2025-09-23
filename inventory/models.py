from django.db import models
from decimal import Decimal
from common.models import TimeStampedModel, Company

class Warehouse(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

class Product(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    barcode = models.CharField(max_length=64, blank=True)

class StockLot(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    quantity_remaining = models.DecimalField(max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4)

class StockMove(TimeStampedModel):
    IN, OUT = ("IN","OUT")
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    type = models.CharField(max_length=3, choices=[(IN,"IN"),(OUT,"OUT")])
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0.0000"))
    ref = models.CharField(max_length=100, blank=True)
    date = models.DateField()
