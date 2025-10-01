from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

ADMIN_URLS = [
    "/admin/ledger/reportcenterproxy/trial-balance/",
    "/admin/ledger/reportcenterproxy/general-ledger/",
    "/admin/ledger/reportcenterproxy/balance-sheet/",
    "/admin/ledger/reportcenterproxy/income-statement/",
]

class AdminReportSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="ci_admin",
            email="ci@example.com",
            password="ci",
            is_staff=True,
            is_superuser=True,
        )

    def setUp(self):
        self.c = Client()
        self.c.force_login(self.user)

    def test_admin_reports_html(self):
        for url in ADMIN_URLS:
            with self.subTest(url=url):
                r = self.c.get(f"{url}?from=2025-09-01&to=2025-09-30")
                self.assertEqual(r.status_code, 200)

    def test_trial_balance_xlsx(self):
        url = "/admin/ledger/reportcenterproxy/trial-balance/"
        r = self.c.get(f"{url}?from=2025-09-01&to=2025-09-30&format=xlsx")
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", r["Content-Type"])

    def test_gl_xlsx(self):
        url = "/admin/ledger/reportcenterproxy/general-ledger/"
        r = self.c.get(f"{url}?from=2025-09-01&to=2025-09-30&format=xlsx")
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", r["Content-Type"])
