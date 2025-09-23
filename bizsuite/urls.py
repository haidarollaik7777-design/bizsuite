from importlib import import_module
from importlib import import_module
from django.http import HttpResponse
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.decorators.csrf import csrf_exempt
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# --- lazy wrappers for csvdebug (avoid import-time issues) ---
from importlib import import_module

def _csv_public_view(request, *args, **kwargs):
    m = import_module('bizsuite.csvdebug')
    return m.trial_balance_csv_public(request, *args, **kwargs)

def _csv_view(request, *args, **kwargs):
    m = import_module('bizsuite.csvdebug')
    return m.trial_balance_csv(request, *args, **kwargs)
# --- end wrappers ---

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Only import the helper that actually exists
from ledger.views_email import email_invoice, invoice_pdf_debug

from ledger.views_email import email_invoice, invoice_pdf_debug
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("api/inventory/", include("inventory.urls")),
    path("api/ledger/", include("ledger.urls")),
    path("api/reports/", include("reports.urls")),

    # Email invoice helper endpoint
    path("api/ledger/invoices/<int:pk>/email/", email_invoice, name="invoice-email"),
    path('api/ledger/invoices/<int:pk>/pdf-debug/', invoice_pdf_debug, name='invoice-pdf-debug'),
    path('api/reports/profit-loss.csv', profit_loss_csv),
    path('api/reports/trial-balance-public.csv', _csv_public_view, name='trial-balance-csv-public'),
    path('api/reports/trial-balance.csv', _csv_view, name='trial-balance-csv'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)












# Serve static in dev
urlpatterns += staticfiles_urlpatterns()






def reports_tester(request):
    return HttpResponse("reports tester ok", content_type="text/plain")

# ---- reports tester (inline) ----
from django.http import HttpResponse
def reports_tester(request):
    return HttpResponse("reports tester ok", content_type="text/plain")

try:
    urlpatterns
except NameError:
    urlpatterns = [
    path('api/reports/profit-loss.csv', profit_loss_csv),
    path('api/reports/trial-balance-public.csv', _csv_public_view, name='trial-balance-csv-public'),
    path('api/reports/trial-balance.csv', _csv_view, name='trial-balance-csv'),
]

# add once
if not any(getattr(p, 'pattern', None) and 'api/reports/tester/' in str(p.pattern) for p in urlpatterns):
    from django.urls import path
    urlpatterns += [path('api/reports/tester/', reports_tester)]
# ---- end tester ----

# --- debug CSV routes (project-level) ---
try:
    urlpatterns += [
        path('api/reports/tb-public.csv', trial_balance_csv_public, name='tb-public-csv'),
        path('api/reports/tb.csv',        trial_balance_csv,        name='tb-csv'),
    ]
except NameError:
    urlpatterns = [
        path('api/reports/tb-public.csv', trial_balance_csv_public, name='tb-public-csv'),
        path('api/reports/tb.csv',        trial_balance_csv,        name='tb-csv'),
    path('api/reports/profit-loss.csv', profit_loss_csv),
    path('api/reports/trial-balance-public.csv', _csv_public_view, name='trial-balance-csv-public'),
    path('api/reports/trial-balance.csv', _csv_view, name='trial-balance-csv'),
]
# --- end debug CSV routes ---