from django.urls import path
from . import views_api as v

urlpatterns = [
    path('invoices/', v.invoices_list),
    path('invoices/<int:pk>/pdf/', v.invoice_pdf),
    path('invoices/<int:pk>/email/', v.invoice_email, name='invoice-email'),
]