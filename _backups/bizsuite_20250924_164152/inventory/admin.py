from django.contrib import admin
from .models import Warehouse, Product, StockLot, StockMove
admin.site.register(Warehouse); admin.site.register(Product); admin.site.register(StockLot); admin.site.register(StockMove)
