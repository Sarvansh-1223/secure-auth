import re
from datetime import date

from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from accounts.models import User, UserProfile

API = "/api/v1"


class AuthTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        mail.outbox = []

    # ---- helpers
    def client_for_device(self, ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15", csrf=False):
        c = APIClient(enforce_csrf_checks=csrf, HTTP_USER_AGENT=ua)
        return c

    def make_user(self, email="alice@example.com", phone=None, verified=True):
        user = User.objects.create_user(email=email, phone_e164=phone, email_verified=bool(email) and verified,
                                        phone_verified=bool(phone) and verified)
        UserProfile.objects.create(user=user, surname="Smith", date_of_birth=date(1990, 1, 1))
        return user

    def last_code(self):
        self.assertTrue(mail.outbox, "no email was sent")
        match = re.search(r"\b(\d{6})\b", mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def request_code(self, client, identifier):
        cache.clear()  # skip resend cooldown unless the test is about it
        return client.post(f"{API}/auth/otp/request", {"identifier": identifier}, format="json")

    def login_otp(self, client, identifier="alice@example.com"):
        self.request_code(client, identifier)
        r = client.post(f"{API}/auth/otp/verify", {"identifier": identifier, "code": self.last_code()}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        return r

    def wrong_code(self, client, identifier="alice@example.com", code="000000"):
        return client.post(f"{API}/auth/otp/verify", {"identifier": identifier, "code": code}, format="json")
