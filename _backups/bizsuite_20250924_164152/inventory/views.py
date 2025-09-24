from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import date
from .models import Warehouse, Product, StockLot, StockMove
from .serializers import WarehouseSerializer, ProductSerializer, StockLotSerializer, StockMoveSerializer
from .services import receive, ship

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

class StockMoveViewSet(viewsets.ModelViewSet):
    queryset = StockMove.objects.all()
    serializer_class = StockMoveSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def receive_api(self, request):
        pid = request.data.get('product_id'); wid = request.data.get('warehouse_id')
        qty = request.data.get('qty'); cost = request.data.get('unit_cost')
        d = request.data.get('date') or str(date.today())
        from .models import Product, Warehouse
        p = Product.objects.get(id=pid); w = Warehouse.objects.get(id=wid)
        receive(p, w, qty, cost, d, ref='API-RECEIPT')
        return Response({'status':'received'})

    @action(detail=False, methods=['post'])
    def ship_api(self, request):
        pid = request.data.get('product_id'); wid = request.data.get('warehouse_id')
        qty = request.data.get('qty'); d = request.data.get('date') or str(date.today())
        from .models import Product, Warehouse
        p = Product.objects.get(id=pid); w = Warehouse.objects.get(id=wid)
        ship(p, w, qty, d, ref='API-SHIP')
        return Response({'status':'shipped'})
