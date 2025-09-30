from io import StringIO
import csv
from datetime import datetime
from django.http import HttpResponse

def rows_to_csv_response(filename: str, headers, rows):
    buf = StringIO()
    w = csv.writer(buf)
    if headers:
        w.writerow(headers)
    for r in rows:
        w.writerow(list(r))
    resp = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    return resp

def safe_date(s, default):
    if not s:
        return default
    s = str(s).strip()
    for fmt in ("%Y-%m-%d","%m/%d/%Y","%b %d, %Y","%b. %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return default