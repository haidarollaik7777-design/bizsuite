from django.urls import path
from . import views

urlpatterns = [
    path("trial-balance/", views.report_trial_balance, name="report_trial_balance"),
    path("general-ledger/", views.report_general_ledger, name="report_general_ledger"),
    path("income-statement/", views.report_income_statement, name="report_income_statement"),
    path("balance-sheet/", views.report_balance_sheet, name="report_balance_sheet"),

    # export uses same views via ?format=csv|xlsx
    path("export/csv/trial-balance/", views.report_trial_balance, name="csv_trial_balance"),
    path("export/xlsx/trial-balance/", views.report_trial_balance, name="xlsx_trial_balance"),
    path("export/csv/general-ledger/", views.report_general_ledger, name="csv_general_ledger"),
    path("export/xlsx/general-ledger/", views.report_general_ledger, name="xlsx_general_ledger"),
    path("export/csv/income-statement/", views.report_income_statement, name="csv_income_statement"),
    path("export/xlsx/income-statement/", views.report_income_statement, name="xlsx_income_statement"),
    path("export/csv/balance-sheet/", views.report_balance_sheet, name="csv_balance_sheet"),
    path("export/xlsx/balance-sheet/", views.report_balance_sheet, name="xlsx_balance_sheet"),
]