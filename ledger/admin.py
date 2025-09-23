from django.contrib import admin
from .models import Account, Journal, JournalEntry, JournalLine, Tax, Invoice, InvoiceLine
admin.site.register(Account); admin.site.register(Journal); admin.site.register(JournalEntry); admin.site.register(JournalLine); admin.site.register(Tax); admin.site.register(Invoice); admin.site.register(InvoiceLine)
