from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from django.apps import apps

MONEY_Q = Decimal("0.01")

def _fmt_money(x, cur="USD"):
    try: return f"{Decimal(x).quantize(MONEY_Q, ROUND_HALF_UP):,.2f} {cur}"
    except Exception: return f"{x} {cur}"

def render_voucher_pdf_bytes(v):
    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Voucher {v.pk}",
                            leftMargin=14*mm, rightMargin=14*mm, topMargin=14*mm, bottomMargin=14*mm)
    story=[]
    story.append(Paragraph("<b>PAYMENT VOUCHER</b>", styles["Title"]))
    company = getattr(v,"company",None); company_name = getattr(company,"name","Company")
    story.append(Paragraph(company_name, styles["Heading3"]))
    date = getattr(v,"date", timezone.now().date())
    payee = getattr(v,"payee_name", None) or getattr(getattr(v,"partner",None),"name","")
    curr  = getattr(getattr(v,"company",None),"currency","USD")
    amount = getattr(v,"amount", None)
    rows = [
        ["Voucher #", str(getattr(v,"pk",""))],
        ["Date", str(date)],
        ["Payee", payee or "?"],
        ["Amount", _fmt_money(amount or 0, curr)],
        ["Reference", getattr(v,"reference","")],
        ["Notes", getattr(v,"notes","")],
    ]
    tbl = Table(rows, colWidths=[30*mm, 130*mm])
    tbl.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.whitesmoke)]))
    story += [Spacer(1,6), tbl]
    doc.build(story)
    return buf.getvalue()

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def voucher_pdf(request, pk:int):
    Voucher = apps.get_model("ledger","Voucher") or apps.get_model("payments","Voucher")
    if Voucher is None: raise Http404("Voucher model not found")
    try: v = Voucher.objects.select_related("company","partner").get(pk=pk)
    except Exception: raise Http404("Voucher not found")
    return FileResponse(BytesIO(render_voucher_pdf_bytes(v)), as_attachment=False,
                        filename=f"voucher_{pk}.pdf", content_type="application/pdf")
