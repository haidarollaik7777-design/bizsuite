from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def build_invoice_pdf(path, invoice):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    c.setFont('Helvetica-Bold', 14)
    c.drawString(40, h-40, f"Invoice #{invoice.id}")
    c.setFont('Helvetica', 10)
    c.drawString(40, h-60, f"Date: {invoice.date}")
    c.drawString(40, h-80, f"Customer: {invoice.partner.name}")
    y = h-120; total = 0.0
    c.drawString(40, y, "Items:"); y-=20
    for line in invoice.lines.all():
        amt = float(line.quantity * line.unit_price); total += amt
        c.drawString(60, y, f"{line.product_name}  x{line.quantity} @ {line.unit_price} = {amt:.2f}")
        y -= 15
    c.drawString(40, y-10, f"Total: {total:.2f}")
    c.showPage(); c.save()
