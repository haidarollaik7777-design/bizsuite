from bizsuite.csvdebug import tb_auto_csv
from django.urls import path
from . import views as v

urlpatterns = [
    path("export/xlsx/trial-balance/", views.report_trial_balance, name="xlsx_trial_balance"),
    path("export/csv/trial-balance/", views.report_trial_balance, name="csv_trial_balance"),
    path("trial-balance/", views.report_trial_balance, name="report_trial_balance"),
    path("export/xlsx/general-ledger/", views.report_general_ledger, name="xlsx_general_ledger"),
    path("export/csv/general-ledger/", views.report_general_ledger, name="csv_general_ledger"),
    path("general-ledger/", views.report_general_ledger, name="report_general_ledger"),
    path('export/xlsx/trial-balance/', views.report_trial_balance, name='xlsx_trial_balance'),
    path('export/csv/trial-balance/', views.report_trial_balance, name='csv_trial_balance'),
    path('trial-balance/', views.report_trial_balance, name='report_trial_balance'),
    path('export/xlsx/general-ledger/', views.report_general_ledger, name='xlsx_general_ledger'),
    path('export/csv/general-ledger/', views.report_general_ledger, name='csv_general_ledger'),
    path('general-ledger/', views.report_general_ledger, name='report_general_ledger'),
    path('tb-auto.csv', tb_auto_csv, name='tb-auto-csv'),
    path('trial-balance/',    v.trial_balance_api, name='trial-balance'),
    path('profit-loss/',      v.profit_loss_api,   name='profit-loss'),
    path('tester/',           v.reports_tester,    name='reports-tester'),
    path('trial-balance.csv', v.trial_balance_csv_simple),
    path('ping.csv', v.csv_ping),
]







