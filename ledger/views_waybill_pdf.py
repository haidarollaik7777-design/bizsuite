from io import BytesIO
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

def render_waybill_pdf_bytes(sh):
    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Waybill {sh.pk}",
                            leftMargin=14*mm, rightMargin=14*mm, topMargin=14*mm, bottomMargin=14*mm)
    story=[]
    story.append(Paragraph("<b>WAYBILL</b>", styles["Title"]))
    date = getattr(sh,"date", timezone.now().date())
    rows = [
        ["Waybill #", str(getattr(sh,"pk",""))],
        ["Date", str(date)],
        ["Shipper", getattr(getattr(sh,"shipper",None),"name", getattr(sh,"shipper_name","") or "?")],
        ["Consignee", getattr(getattr(sh,"consignee",None),"name", getattr(sh,"consignee_name","") or "?")],
        ["From", getattr(sh,"origin","")], ["To", getattr(sh,"destination","")],
    ]
    tbl = Table(rows, colWidths=[30*mm, 130*mm])
    tbl.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.whitesmoke)]))
    story += [Spacer(1,6), tbl]
    # simple items table if available
    items = getattr(sh,"items",None); items = getattr(items,"all",lambda:[])()
    if items:
        data = [["#", "Description", "Qty"]]
        for i,it in enumerate(items, start=1):
            data.append([str(i), getattr(it,"description", getattr(getattr(it,"product",None),"name","Item")), str(getattr(it,"quantity",1))])
        itbl = Table(data, colWidths=[10*mm,120*mm,30*mm])
        itbl.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.whitesmoke)]))
        story += [Spacer(1,6), itbl]
    doc.build(story); return buf.getvalue()

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def waybill_pdf(request, pk:int):
    Shipment = apps.get_model("shipping","Shipment") or apps.get_model("ledger","Shipment") or apps.get_model("inventory","Shipment")
    if Shipment is None: raise Http404("Shipment/Waybill model not found")
    try: sh = Shipment.objects.select_related("shipper","consignee").prefetch_related("items").get(pk=pk)
    except Exception: raise Http404("Waybill not found")
    return FileResponse(BytesIO(render_waybill_pdf_bytes(sh)), as_attachment=False,
                        filename=f"waybill_{pk}.pdf", content_type="application/pdf")
