from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, WorkOrderViewSet, MaintenanceScheduleViewSet

router = DefaultRouter()
router.register(r"assets", AssetViewSet, basename="asset")
router.register(r"workorders", WorkOrderViewSet, basename="workorder")
router.register(r"schedules", MaintenanceScheduleViewSet, basename="schedule")

urlpatterns = [ path("", include(router.urls)) ]
