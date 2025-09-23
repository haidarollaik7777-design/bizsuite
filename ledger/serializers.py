from rest_framework import serializers
from .models import Account, Journal, JournalEntry, JournalLine, Tax, Invoice, InvoiceLine

class AccountSerializer(serializers.ModelSerializer):
    class Meta: model = Account; fields = '__all__'
class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        exclude = ('invoice',)  # parent sets this for nested create

class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True)
    class Meta: model = Invoice; fields = ['id','company','partner','type','date','posted','lines']
    def create(self, validated_data):
        lines = validated_data.pop('lines', [])
        inv = Invoice.objects.create(**validated_data)
        for l in lines:
            InvoiceLine.objects.create(invoice=inv, **l)
        return inv
