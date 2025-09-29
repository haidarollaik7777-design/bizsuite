# reports/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.encoding import smart_str
from django.views.decorators.http import require_GET
import csv, importlib

VALID = {"trial-balance","general-ledger","balance-sheet","income-statement"}
TITLES = {
    "trial-balance": "Trial Balance",
    "general-ledger": "General Ledger",
    "balance-sheet": "Balance Sheet",
    "income-statement": "Income Statement",
}
CSV_NAMES = {
    "trial-balance": "trial_balance.csv",
    "general-ledger": "general_ledger.csv",
    "balance-sheet": "balance_sheet.csv",
    "income-statement": "income_statement.csv",
}

def _error_builder(msg):
    def _b(date_from=None, date_to=None):
        return {"title":"Report Error","columns":["error"],"rows":[{"error":msg}],
                "date_from":date_from,"date_to":date_to}
    return _b

def _builder(slug):
    try:
        rf = importlib.import_module("reports.reports_financial")
    except Exception as e:
        return _error_builder(f"Import reports_financial failed: {e!s}")
    name = {
        "trial-balance":"build_trial_balance",
        "general-ledger":"build_general_ledger",
        "balance-sheet":"build_balance_sheet",
        "income-statement":"build_income_statement",
    }[slug]
    fn = getattr(rf, name, None)
    return fn or _error_builder(f"Builder '{name}' missing in reports/reports_financial.py")

@staff_member_required
@require_GET
def report_center_proxy(request, report_id: str):
    if report_id not in VALID:
        raise Http404(f"Report with ID '{report_id}' doesn't exist.")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    fmt = (request.GET.get("format") or "").lower()

    builder = _builder(report_id)
    try:
        payload = builder(date_from=date_from, date_to=date_to)
    except Exception as e:
        payload = {"title":TITLES[report_id],"columns":["error"],
                   "rows":[{"error":f"Runtime error: {e!s}"}],
                   "date_from":date_from,"date_to":date_to}

    columns = payload.get("columns", [])
    rows = payload.get("rows", [])

    if fmt == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{smart_str(CSV_NAMES[report_id])}"'
        writer = csv.DictWriter(resp, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in columns})
        return resp

    return render(request, "reports/report_center_proxy.html", {
        "title": TITLES[report_id],
        "columns": columns,
        "rows": rows,
        "date_from": payload.get("date_from"),
        "date_to": payload.get("date_to"),
        "report_id": report_id,
        "debug_rows": None,
    })
