from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, ProductViewSet, StockMoveViewSet

router = DefaultRouter()
router.register('warehouses', WarehouseViewSet)
router.register('products', ProductViewSet)
router.register('moves', StockMoveViewSet)

urlpatterns = [ path('', include(router.urls)) ]
