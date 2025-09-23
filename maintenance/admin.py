from django.contrib import admin
from .models import Asset, WorkOrder, MaintenanceSchedule
admin.site.register(Asset)
admin.site.register(WorkOrder)
admin.site.register(MaintenanceSchedule)
