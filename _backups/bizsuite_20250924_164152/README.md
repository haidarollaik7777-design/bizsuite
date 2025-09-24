# BizSuite Compact (Windows 11)

## Run (dev)
```powershell
python -m venv venv
.env\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Endpoints
- JWT: `POST /api/auth/token/`
- Inventory:
  - `GET /api/inventory/products/`
  - `POST /api/inventory/moves/receive_api/`  {product_id, warehouse_id, qty, unit_cost}
  - `POST /api/inventory/moves/ship_api/`     {product_id, warehouse_id, qty}
- Ledger:
  - `POST /api/ledger/invoices/` (with nested `lines`)
  - `POST /api/ledger/invoices/{id}/post/`  {"ar_account_id":X,"rev_account_id":Y}
- Reports:
  - `GET /api/reports/trial-balance/`
  - `GET /api/reports/pnl/`
  - `GET /api/reports/invoice/{id}/weasy/` (simple PDF via ReportLab)
