from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name="money")
def money(val):
    """1234.5 -> 1,234.50, negatives in parentheses."""
    try:
        x = Decimal(str(val).replace(",", "").strip())
    except Exception:
        return val
    neg = x < 0
    x = abs(x)
    s = f"{x:,.2f}"
    return f"({s})" if neg else s

@register.filter
def get_item(d, key):
    try:
        return d.get(key, "")
    except Exception:
        return ""
