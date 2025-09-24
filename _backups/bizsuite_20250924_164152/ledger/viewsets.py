from rest_framework import viewsets, permissions
from .models import Invoice
from .serializers import InvoiceSerializer  # assumes you already have this

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().order_by("-id")
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
