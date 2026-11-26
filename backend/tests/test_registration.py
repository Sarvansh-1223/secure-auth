from datetime import date, timedelta

from django.core import mail
from django.test import override_settings

from accounts.models import User
from tests.base import API, AuthTestCase

VALID = {"email": "bob@example.com", "surname": "O'Neil-Smith", "date_of_birth": "1992-04-18"}


class RegistrationTests(AuthTestCase):
    def post(self, data, client=None):
        return (client or self.client_for_device()).post(f"{API}/auth/register", data, format="json")

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
        return response.json()["error"]["details"]

    def test_validation_errors(self):
        future = (date.today() + timedelta(days=1)).isoformat()
        self.assertIn("date_of_birth", self.errors(self.post({**VALID, "date_of_birth": future})))
        self.assertIn("date_of_birth", self.errors(self.post({**VALID, "date_of_birth": "1800-01-01"})))
        self.assertIn("date_of_birth", self.errors(self.post({**VALID, "date_of_birth": "not-a-date"})))
        self.assertIn("surname", self.errors(self.post({**VALID, "surname": ""})))
        self.assertIn("surname", self.errors(self.post({**VALID, "surname": "<script>"})))
        self.assertIn("email", self.errors(self.post({**VALID, "email": "nope"})))
        self.assertIn("phone", self.errors(self.post({"phone": "12345", "surname": "Lee", "date_of_birth": "1990-01-01"})))
        self.assertIn("identifier", self.errors(self.post({"surname": "Lee", "date_of_birth": "1990-01-01"})))
        self.assertIn("identifier", self.errors(self.post({**VALID, "phone": "+14155552671"})))
        self.assertEqual(User.objects.count(), 0)

    @override_settings(DEBUG=True)  # console SMS provider is DEBUG-only
    def test_register_with_phone_normalises_to_e164(self):
        r = self.post({"phone": "+44 7911 123456", "surname": "Lee", "date_of_birth": "1990-01-01"})
        self.assertEqual(r.status_code, 202)
        self.assertEqual(User.objects.get().phone_e164, "+447911123456")

    def test_register_verify_creates_session_and_marks_verified(self):
        client = self.client_for_device()
        self.assertEqual(self.post(VALID, client).status_code, 202)
        user = User.objects.get(email="bob@example.com")
        self.assertFalse(user.email_verified)

        r = client.post(f"{API}/auth/register/verify", {"identifier": "bob@example.com", "code": self.last_code()}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertIn("sa_session", r.cookies)
        self.assertTrue(r.cookies["sa_session"]["httponly"])
        self.assertEqual(client.get(f"{API}/me").status_code, 200)

    def test_duplicate_registration_is_prevented_and_not_revealed(self):
        self.make_user("bob@example.com")
        r = self.post(VALID)
        fresh = self.post({**VALID, "email": "new@example.com"})
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.json()["message"], fresh.json()["message"])  # indistinguishable
        self.assertEqual(User.objects.filter(email="bob@example.com").count(), 1)
        self.assertIn("already have an account", mail.outbox[0].body)

    def test_email_case_insensitive_unique(self):
        self.make_user("bob@example.com")
        self.post({**VALID, "email": "BOB@Example.com"})
        self.assertEqual(User.objects.count(), 1)

    def test_unverified_registration_can_be_retried(self):
        self.post(VALID)
        self.assertEqual(User.objects.count(), 1)
        from django.core.cache import cache
        cache.clear()
        self.post({**VALID, "surname": "Updated"})
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().profile.surname, "Updated")
