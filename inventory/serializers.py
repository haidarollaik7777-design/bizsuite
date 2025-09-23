from rest_framework import serializers
from .models import Warehouse, Product, StockLot, StockMove

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta: model = Warehouse; fields = '__all__'
class ProductSerializer(serializers.ModelSerializer):
    class Meta: model = Product; fields = '__all__'
class StockLotSerializer(serializers.ModelSerializer):
    class Meta: model = StockLot; fields = '__all__'
class StockMoveSerializer(serializers.ModelSerializer):
    class Meta: model = StockMove; fields = '__all__'
