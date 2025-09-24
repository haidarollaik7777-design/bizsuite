from django.apps import apps
from django.conf import settings

_REQUIRED = {"account", "date", "debit", "credit"}

def _model_has_required_fields(Model):
    names = {f.name for f in Model._meta.get_fields()}
    return _REQUIRED.issubset(names)

def _find_ledger_entry_model():
    model_path = getattr(settings, "LEDGER_ENTRY_MODEL", None)
    if model_path:
        app_label, model_name = model_path.split(".", 1)
        Model = apps.get_model(app_label, model_name)
        if Model and _model_has_required_fields(Model):
            return Model
    for Model in apps.get_models():
        if _model_has_required_fields(Model):
            return Model
    raise LookupError(
        "Could not find a GL model with fields: account, date, debit, credit. "
        "Set settings.LEDGER_ENTRY_MODEL = 'app_label.ModelName' or create such a model."
    )
