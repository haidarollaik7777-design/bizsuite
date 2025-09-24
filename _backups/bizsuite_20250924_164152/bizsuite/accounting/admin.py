from django.contrib import admin
from .models import Account, LedgerEntry



from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.html import format_html
from django.http import Http404

from django.apps import apps
Journal = apps.get_model("accounting", "Journal")
JournalLine = apps.get_model("accounting", "JournalLine")

class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 2
    fields = ("account", "partner", "label", "debit", "credit")
    autocomplete_fields = []
    class Media:
        js = ("accounting/journal_inline_totals.js",)

    try:
        Partner = apps.get_model("common", "Partner")
        autocomplete_fields = ["partner"]
    except Exception:
        pass

@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "company", "description",)
    date_hierarchy = "date"
    search_fields = ("description",)
    list_filter = ("company",)
    inlines = [JournalLineInline]
    change_form_template = "admin/accounting/journal/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<path:object_id>/post/", self.admin_site.admin_view(self.post_view), name="accounting_journal_post"),
        ]
        return custom + urls

    def post_view(self, request, object_id, *args, **kwargs):
        obj = self.get_object(request, object_id)
        if not obj:
            raise Http404("Journal not found")
        try:
            obj.post()
            messages.success(request, "Journal posted to General Ledger.")
        except Exception as e:
            messages.error(request, f"Posting failed: {e}")
        return redirect(f"../../{object_id}/change/")

    def render_change_form(self, request, context, *args, **kwargs):
        # Provide URL for our custom Post button
        obj = context.get("original")
        if obj:
            context["post_url"] = f"./post/"
        return super().render_change_form(request, context, *args, **kwargs)


# ---- Reports: Trial Balance & General Ledger (auto-added) ----
from django.urls import path
from django.db.models import Sum, F, Value as V
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.http import HttpResponse
from django.utils.encoding import smart_str
from django import forms
import csv
from django.apps import apps

Account     = apps.get_model("accounting", "Account")
LedgerEntry = apps.get_model("accounting", "LedgerEntry")
Company     = apps.get_model("common", "Company")

class ReportFilterForm(forms.Form):
    company   = forms.ModelChoiceField(queryset=Company.objects.all(), required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type":"date"}))
    date_to   = forms.DateField(required=False, widget=forms.DateInput(attrs={"type":"date"}))
    account   = forms.ModelChoiceField(queryset=Account.objects.all(), required=False)  # GL use

# Dummy model to host a "Reports" section in admin
from django.db import models
class _ReportCenter(models.Model):
    class Meta:
        managed = False
        verbose_name = "Reports"
        verbose_name_plural = "Reports"



from django.apps import apps
from django.urls import path, reverse
from django.shortcuts import redirect, render
from django.http import HttpResponseRedirect
from django.contrib import admin, messages
from django.utils.safestring import mark_safe

ReportCenter = apps.get_model("accounting", "ReportCenter")

@admin.register(ReportCenter)
class ReportsAdmin(admin.ModelAdmin):
    # When clicking "Reports" in the left menu, go to a hub page with links
    change_list_template = "admin/accounting/reports/hub.html"

    def has_add_permission(self, *a, **k): return False
    def has_change_permission(self, *a, **k): return False
    def has_delete_permission(self, *a, **k): return False

    def get_urls(self):
        # expose the report URLs under this section too
        urls = super().get_urls()
        custom = [
            path("trial-balance/", self.admin_site.admin_view(self.trial_balance_proxy), name="accounting_reports_tb"),
            path("general-ledger/", self.admin_site.admin_view(self.general_ledger_proxy), name="accounting_reports_gl"),
            path("balance-sheet/", self.admin_site.admin_view(self.balance_sheet_proxy), name="accounting_reports_bs"),
            path("income-statement/", self.admin_site.admin_view(self.income_statement_proxy), name="accounting_reports_is"),
        ]
        return custom + urls

    # Proxies just redirect to the real report views we added before
    def trial_balance_proxy(self, request):    return redirect("admin:accounting_trial_balance")
    def general_ledger_proxy(self, request):   return redirect("admin:accounting_general_ledger")
    def balance_sheet_proxy(self, request):    return redirect("admin:accounting_balance_sheet")
    def income_statement_proxy(self, request): return redirect("admin:accounting_income_statement")
