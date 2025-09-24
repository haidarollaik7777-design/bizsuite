from django.http import JsonResponse

def api_root(_request):
    return JsonResponse({
        "ok": True,
        "endpoints": {
            "auth_token":   "/api/auth/token/",
            "auth_refresh": "/api/auth/refresh/",
            "inventory":    "/api/inventory/",
            "ledger":       "/api/ledger/",
            "reports":      "/api/reports/",
        }
    })
