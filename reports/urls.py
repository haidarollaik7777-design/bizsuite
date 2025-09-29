from django.urls import path
from . import views

urlpatterns = [
    path("trial-balance/", views.report_trial_balance, name="report_trial_balance"),
    path("general-ledger/", views.report_general_ledger, name="report_general_ledger"),
    path("income-statement/", views.report_income_statement, name="report_income_statement"),
    path("balance-sheet/", views.report_balance_sheet, name="report_balance_sheet"),
]