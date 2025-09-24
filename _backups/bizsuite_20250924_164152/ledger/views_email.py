from django.http import JsonResponse, HttpResponseBadRequest, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage
from django.conf import settings
import io, json

from .pdf_utils import generate_invoice_pdf_bytes

@csrf_exempt
def email_invoice(request, pk:int):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    try:
        payload = json.loads((request.body or b"").decode("utf-8") or "{}")
    except Exception:
        payload = {}
    to      = payload.get("to") or "test@inbox.local"
    subject = payload.get("subject") or f"Invoice #{pk}"
    message = payload.get("message") or "Attached invoice."

    pdf = generate_invoice_pdf_bytes(pk)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost")
    msg = EmailMessage(subject, message, from_email, [to])
    msg.attach(f"invoice_{pk}.pdf", pdf, "application/pdf")
    sent = msg.send()

    return JsonResponse({"status": "sent" if sent else "not-sent", "attached_bytes": len(pdf), "to": to, "id": pk})

def invoice_pdf_debug(request, pk:int):
    pdf = generate_invoice_pdf_bytes(pk)
    bio = io.BytesIO(pdf)
    resp = FileResponse(bio, as_attachment=True, filename=f"invoice_{pk}_debug.pdf", content_type="application/pdf")
    resp["X-Content-Type-Options"] = "nosniff"
    return resp
