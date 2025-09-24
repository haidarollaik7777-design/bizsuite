from django.urls import path
from .views import trial_balance, profit_and_loss, invoice_pdf_simple
urlpatterns = [
    path('trial-balance/', trial_balance),
    path('pnl/', profit_and_loss),
    path('invoice/<int:invoice_id>/weasy/', invoice_pdf_simple),
]
