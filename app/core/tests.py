from tempfile import TemporaryDirectory

from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse


class HealthTests(TestCase):
    def test_health_checks_database(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})


class ProductionStaticTests(SimpleTestCase):
    def test_collected_admin_css_is_served_with_debug_false(self):
        with TemporaryDirectory() as static_root, override_settings(
            DEBUG=False, STATIC_ROOT=static_root
        ):
            call_command("collectstatic", interactive=False, verbosity=0)
            client = Client()
            plain_url = "/static/admin/css/base.css"
            hashed_url = staticfiles_storage.url("admin/css/base.css")
            self.assertNotEqual(hashed_url, plain_url)

            for url in (plain_url, hashed_url):
                with self.subTest(url=url):
                    response = client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(response["Content-Type"].startswith("text/css"))
                    self.assertIn(b"body", b"".join(response.streaming_content))
                    self.assertIn("Cache-Control", response)
                    if url == hashed_url:
                        self.assertIn("immutable", response["Cache-Control"])
                    response.close()
