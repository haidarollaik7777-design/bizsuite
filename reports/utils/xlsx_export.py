from io import BytesIO
from django.http import HttpResponse

def rows_to_xlsx_response(filename, headers, rows):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except Exception as e:
        return HttpResponse("openpyxl missing: " + str(e), status=500, content_type="text/plain")
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    r = 1
    if headers:
        ws.append(headers); r += 1
        # Bold headers
        for c in range(1, len(headers) + 1):
            ws.cell(row=1, column=c).font = Font(bold=True)
    for row in rows:
        ws.append([("" if v is None else v) for v in row]); r += 1
    bio = BytesIO()
    wb.save(bio); bio.seek(0)
    resp = HttpResponse(
        bio.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    return resp
