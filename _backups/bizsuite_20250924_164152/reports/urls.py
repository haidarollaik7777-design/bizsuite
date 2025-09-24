from bizsuite.csvdebug import tb_auto_csv
from django.urls import path
from . import views as v

urlpatterns = [
    path('tb-auto.csv', tb_auto_csv, name='tb-auto-csv'),
    path('trial-balance/',    v.trial_balance_api, name='trial-balance'),
    path('profit-loss/',      v.profit_loss_api,   name='profit-loss'),
    path('tester/',           v.reports_tester,    name='reports-tester'),
    path('trial-balance.csv', v.trial_balance_csv_simple),
    path('ping.csv', v.csv_ping),
]


