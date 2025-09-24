from rest_framework import serializers
from .models import Asset, WorkOrder, MaintenanceSchedule

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = "__all__"

class WorkOrderSerializer(serializers.ModelSerializer):
    asset_detail = AssetSerializer(source="asset", read_only=True)
    class Meta:
        model = WorkOrder
        fields = "__all__"

class MaintenanceScheduleSerializer(serializers.ModelSerializer):
    asset_detail = AssetSerializer(source="asset", read_only=True)
    class Meta:
        model = MaintenanceSchedule
        fields = "__all__"
