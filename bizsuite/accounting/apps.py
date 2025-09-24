from django.apps import AppConfig

class AccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Full python path to the app package:
    name = "bizsuite.accounting"
    # App label used across relations like "accounting.ModelName":
    label = "accounting"
