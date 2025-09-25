from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # Canonical pages
    path("general-ledger/",     views.report_general_ledger,    name="report_general_ledger"),
    path("trial-balance/",      views.report_trial_balance,     name="report_trial_balance"),
    path("income-statement/",   views.report_income_statement,  name="report_income_statement"),

    # CSV/XLSX are handled by the same views via ?format=...
    path("export/csv/general-ledger/",    views.report_general_ledger,   name="csv_general_ledger"),
    path("export/xlsx/general-ledger/",   views.report_general_ledger,   name="xlsx_general_ledger"),
    path("export/csv/trial-balance/",     views.report_trial_balance,    name="csv_trial_balance"),
    path("export/xlsx/trial-balance/",    views.report_trial_balance,    name="xlsx_trial_balance"),
    path("export/csv/income-statement/",  views.report_income_statement, name="csv_income_statement"),
    path("export/xlsx/income-statement/", views.report_income_statement, name="xlsx_income_statement"),
]
