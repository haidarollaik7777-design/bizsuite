from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

class ReportSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="report_tester", password="testpass", is_staff=True, is_superuser=True
        )

    def setUp(self):
        self.c = Client()
        self.c.login(username="report_tester", password="testpass")

    def _ok(self, url):
        r = self.c.get(url)
        self.assertEqual(r.status_code, 200, f"{url} => {r.status_code}")

    def test_trial_balance_html(self):
        self._ok("/admin/ledger/reportcenterproxy/trial-balance/")

    def test_trial_balance_xlsx(self):
        r = self.c.get("/admin/ledger/reportcenterproxy/trial-balance/?format=xlsx")
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", r["Content-Type"])

    def test_gl_html(self):
        self._ok("/admin/ledger/reportcenterproxy/general-ledger/")

    def test_gl_xlsx(self):
        r = self.c.get("/admin/ledger/reportcenterproxy/general-ledger/?format=xlsx")
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", r["Content-Type"])

    def test_bs_html(self):
        self._ok("/admin/ledger/reportcenterproxy/balance-sheet/")

    def test_is_html(self):
        self._ok("/admin/ledger/reportcenterproxy/income-statement/")
