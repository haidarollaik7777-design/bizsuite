from django import template
register = template.Library()
@register.filter
def get_item(d, key):
    try: return d.get(key, "")
    except Exception: return ""
@register.filter
def money(val):
    try: x = float(val)
    except Exception: return val
    s = f"{abs(x):,.2f}"
    return f"({s})" if x < 0 else s
