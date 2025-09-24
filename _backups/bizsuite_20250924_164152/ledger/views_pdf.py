from io import BytesIO
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from .models import Invoice

def render_invoice_pdf_bytes(invoice):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 20*mm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20*mm, y, f"Invoice #{invoice.id}")
    y -= 8*mm

    c.setFont("Helvetica", 10)
    c.drawString(20*mm, y, f"Date: {getattr(invoice, 'date', timezone.now().date())}")
    y -= 12*mm

    # Lines (if related_name is 'lines', fall back gracefully)
    try:
        items = list(invoice.lines.all())
    except Exception:
        items = []

    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, y, "Items:")
    y -= 8*mm
    c.setFont("Helvetica", 10)

    if not items:
        c.drawString(25*mm, y, "(no lines)")
        y -= 6*mm
    else:
        for ln in items:
            pname = getattr(ln, "product_name", "Item")
            qty   = getattr(ln, "quantity", 1)
            price = getattr(ln, "unit_price", 0)
            c.drawString(25*mm, y, f"- {pname}  x{qty}  @ {price}")
            y -= 6*mm
            if y < 20*mm:
                c.showPage()
                y = height - 20*mm

    c.showPage()
    c.save()
    data = buf.getvalue()
    buf.close()
    return data

def invoice_pdf(request, pk: int):
    inv = get_object_or_404(Invoice, pk=pk)
    pdf = render_invoice_pdf_bytes(inv)
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="invoice_{pk}.pdf"'
    return resp
