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
from decimal import Decimal

@register.filter
def sub(a, b):
    """
    Safe subtraction for template usage: {{ x|sub:y }}
    Works with Decimal/float/int and None.
    """
    try:
        if a is None: a = 0
        if b is None: b = 0
        # Preserve Decimal math if inputs are Decimal
        if isinstance(a, Decimal) or isinstance(b, Decimal):
            a = Decimal(a)
            b = Decimal(b)
        return a - b
    except Exception:
        return 0
