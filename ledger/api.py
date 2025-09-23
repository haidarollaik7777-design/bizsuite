from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountViewSet, InvoiceViewSet

router = DefaultRouter()
router.register('accounts', AccountViewSet)
router.register('invoices', InvoiceViewSet)

urlpatterns = [ path('', include(router.urls)) ]
