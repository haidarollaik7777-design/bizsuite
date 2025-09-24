from rest_framework import viewsets, permissions, filters
from .models import Asset, WorkOrder, MaintenanceSchedule
from .serializers import AssetSerializer, WorkOrderSerializer, MaintenanceScheduleSerializer

class IsAuthenticated(permissions.IsAuthenticated): pass

class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all().order_by("-id")
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name","code","category","location","serial_number","vendor"]
    ordering_fields = ["id","name","code","created_at"]

class WorkOrderViewSet(viewsets.ModelViewSet):
    queryset = WorkOrder.objects.all().order_by("-id")
    serializer_class = WorkOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title","description","assigned_to","asset__name","asset__code"]
    ordering_fields = ["id","due_date","priority","status","created_at"]

class MaintenanceScheduleViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceSchedule.objects.all().order_by("-id")
    serializer_class = MaintenanceScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["asset__name","asset__code"]
    ordering_fields = ["id","frequency_days","next_due","created_at"]
