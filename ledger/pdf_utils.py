# ledger/pdf_utils.py
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def generate_invoice_pdf_bytes(inv_id:int) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Invoice {inv_id}")
    c.drawString(72, 800, f"Invoice #{inv_id}")
    c.drawString(72, 780, "BizSuite diagnostic PDF (valid).")
    c.drawString(72, 760, "Open this in Adobe to confirm attachment integrity.")
    c.showPage()
    c.save()
    return buf.getvalue()
