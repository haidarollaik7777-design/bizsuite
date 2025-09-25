from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # General Ledger
    path("general-ledger/", views.report_general_ledger, name="report_general_ledger"),
    path("export/csv/general-ledger/", views.report_general_ledger, name="csv_general_ledger"),
    path("export/xlsx/general-ledger/", views.report_general_ledger, name="xlsx_general_ledger"),

    # Trial Balance
    path("trial-balance/", views.report_trial_balance, name="report_trial_balance"),
    path("export/csv/trial-balance/", views.report_trial_balance, name="csv_trial_balance"),
    path("export/xlsx/trial-balance/", views.report_trial_balance, name="xlsx_trial_balance"),
]
