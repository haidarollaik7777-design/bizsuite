from decimal import Decimal

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponse
from django import forms
from django.db.models import Sum, Value as V, DecimalField
from django.db.models.functions import Coalesce, Cast

# Ledger models
from .models import Account, Journal, JournalEntry, JournalLine

# Reports hub: prefer ReportCenterProxy (your URL uses /reportcenterproxy/)
try:
    from .models import ReportCenterProxy as ReportsHub
    HUB_TEMPLATE = "admin/ledger/reportcenterproxy/change_list.html"
except Exception:
    ReportsHub = None
    HUB_TEMPLATE = "admin/ledger/reportcenterproxy/change_list.html"

# Optional models (if present)
try:
    from .models import Invoice, InvoiceLine, Tax
except Exception:
    Invoice = InvoiceLine = Tax = None

# Optional Company filter
try:
    from common.models import Company
except Exception:
    Company = None


# --- Auto-register regular ledger models (so they reappear in Admin) ---
for m in (Account, Journal, JournalEntry, JournalLine, Invoice, InvoiceLine, Tax):
    if m and m not in admin.site._registry:
        try:
            admin.site.register(m)
        except admin.sites.AlreadyRegistered:
            pass


# --- Shared filters ---
class ReportFilterForm(forms.Form):
    if Company:
        company = forms.ModelChoiceField(queryset=Company.objects.all(), required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to   = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    account   = forms.ModelChoiceField(queryset=Account.objects.all(), required=False)

def _filtered_lines(request):
    qs = JournalLine.objects.select_related("account", "entry").all()
    form = ReportFilterForm(request.GET or None)
    if form.is_valid():
        cd = form.cleaned_data
        if Company and cd.get("company"):
            qs = qs.filter(entry__company=cd["company"])
        if cd.get("date_from"):
            qs = qs.filter(entry__date__gte=cd["date_from"])
        if cd.get("date_to"):
            qs = qs.filter(entry__date__lte=cd["date_to"])
        if cd.get("account"):
            qs = qs.filter(account=cd["account"])
    return form, qs


# --- Trial Balance (Decimal-safe) ---
def tb_view(request, admin_site):
    form, qs = _filtered_lines(request)

    dfield = DecimalField(max_digits=18, decimal_places=2)
    zero   = V(Decimal("0.00"), output_field=dfield)

    agg = qs.values("account_id", "account__code", "account__name").annotate(
        dr=Coalesce(Cast(Sum("debit"),  dfield), zero),
        cr=Coalesce(Cast(Sum("credit"), dfield), zero),
    ).order_by("account__code")

    rows = []
    total_dr = Decimal("0.00")
    total_cr = Decimal("0.00")
    for a in agg:
        dr = Decimal(a["dr"] or 0)
        cr = Decimal(a["cr"] or 0)
        rows.append({
            "code": a["account__code"],
            "name": a["account__name"],
            "dr": dr,
            "cr": cr,
            "balance": dr - cr,
        })
        total_dr += dr
        total_cr += cr

    if request.GET.get("export") == "csv":
        import csv
        from django.utils.encoding import smart_str
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="trial_balance.csv"'
        w = csv.writer(resp)
        w.writerow(["Code", "Account", "Debit", "Credit", "Balance"])
        for r in rows:
            w.writerow([smart_str(r["code"]), smart_str(r["name"]),
                        f"{r['dr']:.2f}", f"{r['cr']:.2f}", f"{r['balance']:.2f}"])
        w.writerow([])
        w.writerow(["TOTAL", "", f"{total_dr:.2f}", f"{total_cr:.2f}", f"{(total_dr - total_cr):.2f}"])
        return resp

    ctx = {
        **admin_site.each_context(request),
        "title": "Trial Balance",
        "form": form,
        "rows": rows,
        "total_dr": total_dr,
        "total_cr": total_cr,
        "total_diff": total_dr - total_cr,
    }
    try:
        return render(request, "admin/accounting/reports/trial_balance.html", ctx)
    except Exception:
        return HttpResponse("<h1>Trial Balance</h1>" + str(rows))


# --- General Ledger (Decimal-safe running balance) ---
def gl_view(request, admin_site):
    form, qs = _filtered_lines(request)
    entries = qs.order_by("entry__date", "id")

    run = []
    bal = Decimal("0.00")
    for e in entries:
        dr = Decimal(getattr(e, "debit", 0) or 0)
        cr = Decimal(getattr(e, "credit", 0) or 0)
        bal += (dr - cr)
        run.append((e, bal))

    if request.GET.get("export") == "csv":
        import csv
        from django.utils.encoding import smart_str
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="general_ledger.csv"'
        w = csv.writer(resp)
        w.writerow(["Date", "Account", "Reference", "Description", "Debit", "Credit", "Running Balance"])
        for e, b in run:
            dt  = getattr(e.entry, "date", "")
            ref = getattr(e.entry, "reference", "")
            desc= getattr(e, "label", "")
            w.writerow([dt, smart_str(e.account), smart_str(ref), smart_str(desc),
                        f"{Decimal(getattr(e,'debit',0) or 0):.2f}",
                        f"{Decimal(getattr(e,'credit',0) or 0):.2f}",
                        f"{b:.2f}"])
        return resp

    ctx = {**admin_site.each_context(request), "title": "General Ledger", "form": form, "rows": run}
    try:
        return render(request, "admin/accounting/reports/general_ledger.html", ctx)
    except Exception:
        return HttpResponse("<h1>General Ledger</h1>" + str([(str(e), b) for e, b in run]))


# --- Admin registration for the hub ---
if ReportsHub:
    @admin.register(ReportsHub)
    class ReportCenterAdmin(admin.ModelAdmin):
        change_list_template = HUB_TEMPLATE
        def has_add_permission(self, *a, **k): return False
        def has_change_permission(self, *a, **k): return False
        def has_delete_permission(self, *a, **k): return False
        def get_urls(self):
            urls = super().get_urls()
            # NOTE: these lambdas call the functions defined ABOVE (single source of truth)
            return [
                path("trial-balance/",  self.admin_site.admin_view(lambda r: tb_view(r, self.admin_site)), name="ledger_trial_balance"),
                path("general-ledger/", self.admin_site.admin_view(lambda r: gl_view(r, self.admin_site)), name="ledger_general_ledger"),
            ] + urls
else:
    # If the hub model is missing, still expose the views under admin root to test
    @admin.register(JournalLine)
    class _TempAdmin(admin.ModelAdmin):
        change_list_template = "admin/base_site.html"
        def get_urls(self):
            urls = super().get_urls()
            return [
                path("reports/trial-balance/",  self.admin_site.admin_view(lambda r: tb_view(r, self.admin_site))),
                path("reports/general-ledger/", self.admin_site.admin_view(lambda r: gl_view(r, self.admin_site))),
            ] + urls

