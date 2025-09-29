# reports/report_registry.py
from .reports_financial import (
    build_trial_balance,
    build_general_ledger,
    build_balance_sheet,
    build_income_statement,
)

REPORTS = {
    "trial-balance": {
        "title": "Trial Balance",
        "builder": build_trial_balance,
        "csv_filename": "trial_balance.csv",
    },
    "general-ledger": {
        "title": "General Ledger",
        "builder": build_general_ledger,
        "csv_filename": "general_ledger.csv",
    },
    "balance-sheet": {
        "title": "Balance Sheet",
        "builder": build_balance_sheet,
        "csv_filename": "balance_sheet.csv",
    },
    "income-statement": {
        "title": "Income Statement",
        "builder": build_income_statement,
        "csv_filename": "income_statement.csv",
    },
}
