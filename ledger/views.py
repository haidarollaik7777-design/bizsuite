from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Account, Invoice
from .serializers import AccountSerializer, InvoiceSerializer
from .services import post_invoice
from .models import Account as Acc

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def post(self, request, pk=None):
        inv = self.get_object()
        ar_id = request.data.get('ar_account_id')
        rev_id = request.data.get('rev_account_id')
        if not (ar_id and rev_id):
            return Response({'detail':'ar_account_id and rev_account_id are required'}, status=400)
        post_invoice(inv, Acc.objects.get(id=ar_id), Acc.objects.get(id=rev_id))
        return Response({'status':'posted'})
