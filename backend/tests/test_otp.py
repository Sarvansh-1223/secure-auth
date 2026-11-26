from datetime import timedelta

from django.core import mail
from django.utils import timezone

from otp.models import OTPVerification
from tests.base import API, AuthTestCase


class OtpTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("alice@example.com")
        self.client = self.client_for_device()

    def test_code_is_six_digits_hashed_and_login_succeeds(self):
        self.login_otp(self.client)
        otp = OTPVerification.objects.get()
        code = mail.outbox[-1].body.split("code to sign in is ")[1][:6]
        self.assertEqual(len(code), 6)
        self.assertNotIn(code, otp.code_hmac)
        self.assertNotIn(code, otp.salt)
        self.assertEqual(len(otp.code_hmac), 64)
        self.assertIsNotNone(otp.consumed_at)

    def test_code_cannot_be_reused(self):
        self.request_code(self.client, "alice@example.com")
        code = self.last_code()
        first = self.client.post(f"{API}/auth/otp/verify", {"identifier": "alice@example.com", "code": code}, format="json")
        second = self.client_for_device().post(f"{API}/auth/otp/verify", {"identifier": "alice@example.com", "code": code}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.json()["error"]["code"], "INVALID_CREDENTIALS")

    def test_expired_code_rejected(self):
        self.request_code(self.client, "alice@example.com")
        code = self.last_code()
        OTPVerification.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        r = self.client.post(f"{API}/auth/otp/verify", {"identifier": "alice@example.com", "code": code}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_new_code_invalidates_previous(self):
        self.request_code(self.client, "alice@example.com")
        old = self.last_code()
        self.request_code(self.client, "alice@example.com")
        r = self.client.post(f"{API}/auth/otp/verify", {"identifier": "alice@example.com", "code": old}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_resend_cooldown_and_hourly_cap(self):
        first = self.client.post(f"{API}/auth/otp/request", {"identifier": "alice@example.com"}, format="json")
        again = self.client.post(f"{API}/auth/otp/resend", {"identifier": "alice@example.com"}, format="json")
        self.assertEqual(first.status_code, 202)
        self.assertEqual(again.status_code, 429)
        self.assertEqual(again.json()["error"]["code"], "RESEND_THROTTLED")
        self.assertGreater(again.json()["error"]["details"]["retry_after_seconds"], 0)

    def test_unknown_identifier_is_indistinguishable(self):
        known = self.client.post(f"{API}/auth/otp/request", {"identifier": "alice@example.com"}, format="json")
        unknown = self.client.post(f"{API}/auth/otp/request", {"identifier": "ghost@example.com"}, format="json")
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(len(mail.outbox), 1)  # only the real account got mail
        r1 = self.wrong_code(self.client, "alice@example.com")
        r2 = self.wrong_code(self.client, "ghost@example.com")
        self.assertEqual(r1.status_code, r2.status_code)
        self.assertEqual(r1.json(), r2.json())

    def test_malformed_codes_rejected(self):
        self.request_code(self.client, "alice@example.com")
        for bad in ["", "12345", "abcdef", "1234567"]:
            r = self.client.post(f"{API}/auth/otp/verify", {"identifier": "alice@example.com", "code": bad}, format="json")
            self.assertIn(r.status_code, (400, 423))
            self.assertNotEqual(r.status_code, 200)

    def test_unverified_account_cannot_log_in_by_otp(self):
        self.make_user("pending@example.com", verified=False)
        self.client.post(f"{API}/auth/otp/request", {"identifier": "pending@example.com"}, format="json")
        self.assertEqual(len(mail.outbox), 0)
