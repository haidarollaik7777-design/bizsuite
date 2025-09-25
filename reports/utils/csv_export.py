from io import StringIO
import csv
from datetime import datetime
from django.http import HttpResponse

def safe_date(s, default):
    """
    Accepts 'YYYY-MM-DD' or 'MM/DD/YYYY' (and blanks) and returns a date.
    Falls back to default if parse fails.
    """
    if not s:
        return default
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return default

def rows_to_csv_response(filename, headers, rows):
    # filename without extension
    f = StringIO()
    writer = csv.writer(f)
    if headers:
        writer.writerow(headers)
    for r in rows:
        writer.writerow([("" if v is None else v) for v in r])
    data = f.getvalue().encode("utf-8-sig")
    resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    return resp
