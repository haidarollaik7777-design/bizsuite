# Reports (Admin)

## URLs
- Trial Balance: `/admin/ledger/reportcenterproxy/trial-balance/`
- General Ledger: `/admin/ledger/reportcenterproxy/general-ledger/`
- Balance Sheet: `/admin/ledger/reportcenterproxy/balance-sheet/`
- Income Statement: `/admin/ledger/reportcenterproxy/income-statement/`

## Date Range & Export
- Query params:
  - `from=YYYY-MM-DD` (optional)
  - `to=YYYY-MM-DD` (optional)
  - `format=xlsx` (optional; when present, downloads Excel)
- Examples:
  - HTML: `/admin/ledger/reportcenterproxy/trial-balance/?from=2025-09-01&to=2025-09-30`
  - Excel: `/admin/ledger/reportcenterproxy/trial-balance/?from=2025-09-01&to=2025-09-30&format=xlsx`
- If `from`/`to` are omitted or blank, the report includes all available data.

## Notes
- In PowerShell, when testing a full URL that contains `&`, wrap it in quotes:
  `Start-Process "http://127.0.0.1:8000/admin/ledger/reportcenterproxy/trial-balance/?from=2025-09-01&to=2025-09-30&format=xlsx"`
