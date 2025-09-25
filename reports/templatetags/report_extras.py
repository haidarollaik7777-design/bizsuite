from django import template
from urllib.parse import urlencode

# Minimal, safe library. Does NOT override builtin filters (e.g., no "add" here).
register = template.Library()

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """Build a querystring from current request.GET + kwargs (doseq supported)."""
    request = context.get("request")
    base = {}
    try:
        if request and hasattr(request, "GET"):
            # Django QueryDict supports lists; keep doseq behavior.
            for k in request.GET.keys():
                vals = request.GET.getlist(k)
                base[k] = vals if len(vals) > 1 else request.GET.get(k)
    except Exception:
        pass
    for k, v in kwargs.items():
        if v is None or v == "":
            continue
        base[k] = v
    return urlencode(base, doseq=True)

@register.filter
def money(value, ndigits=2):
    """Format a number with fixed decimals (default 2)."""
    try:
        return f"{float(value or 0):.{int(ndigits)}f}"
    except Exception:
        return value

@register.filter
def nz(value, default=0):
    """Return default if value is None/empty."""
    return value if value not in (None, "") else default
