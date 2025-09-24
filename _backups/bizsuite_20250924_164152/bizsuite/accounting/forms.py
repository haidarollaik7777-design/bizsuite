from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps

def _partner_model_or_none():
    try:
        return apps.get_model("common", "Partner")
    except Exception:
        return None

class JournalLineForm(forms.ModelForm):
    class Meta:
        model = apps.get_model("accounting", "JournalLine")
        fields = ["account", "partner", "label", "debit", "credit"]
        widgets = {
            "label":  forms.TextInput(attrs={"placeholder": "e.g., Cash sale"}),
            "debit":  forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "credit": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def clean(self):
        cleaned = super().clean()
        debit  = cleaned.get("debit")  or 0
        credit = cleaned.get("credit") or 0
        if (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
            raise ValidationError("Enter either Debit or Credit (one side > 0), not both and not both zero.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        # Auto-fill label if blank from account name
        if not getattr(obj, "label", "") and getattr(obj, "account_id", None):
            try:
                obj.label = str(obj.account)
            except Exception:
                pass
        if commit:
            obj.save()
        return obj
