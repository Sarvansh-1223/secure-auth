from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from sessions_app.models import Device, UserSession
from tests.base import API, AuthTestCase

MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1"


class SingleDeviceTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("alice@example.com")

    def test_new_login_revokes_previous_device_immediately(self):
        a, b = self.client_for_device(MAC), self.client_for_device(IPHONE)
        self.login_otp(a)
        self.assertEqual(a.get(f"{API}/me").status_code, 200)

        self.login_otp(b)

        old = a.get(f"{API}/me")
        self.assertEqual(old.status_code, 401)
        self.assertEqual(old.json()["error"]["code"], "SESSION_REPLACED")
        self.assertEqual(b.get(f"{API}/me").status_code, 200)
        self.assertEqual(a.get(f"{API}/security/settings").status_code, 401)  # every protected API

        sessions = UserSession.objects.filter(user=self.user)
        self.assertEqual(sessions.filter(revoked_at__isnull=True).count(), 1)
        self.assertEqual(sessions.get(active_slot__isnull=True).revoked_reason, "REPLACED")

    def test_database_forbids_two_active_sessions(self):
        self.login_otp(self.client_for_device(MAC))
        existing = UserSession.objects.get()
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserSession.objects.create(
                user=self.user, device=existing.device, token_hash="x" * 64, active_slot=1,
                auth_method="OTP", last_activity_at=timezone.now(), expires_at=timezone.now() + timedelta(hours=1),
            )

    def test_logout_invalidates_server_side(self):
        a = self.client_for_device(MAC)
        r = self.login_otp(a)
        stolen_cookie = r.cookies["sa_session"].value
        self.assertEqual(a.post(f"{API}/auth/logout", {}, format="json").status_code, 200)

        replay = self.client_for_device(MAC)
        replay.cookies["sa_session"] = stolen_cookie  # attacker replays the old cookie
        res = replay.get(f"{API}/me")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["error"]["code"], "SESSION_ENDED")
        self.assertEqual(UserSession.objects.filter(active_slot=1).count(), 0)

    def test_idle_and_absolute_expiry(self):
        a = self.client_for_device(MAC)
        self.login_otp(a)
        UserSession.objects.update(last_activity_at=timezone.now() - timedelta(hours=1))
        r = a.get(f"{API}/me")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (401, "SESSION_EXPIRED"))
        self.assertEqual(UserSession.objects.filter(active_slot=1).count(), 0)

    def test_tokens_stored_hashed_and_device_tracked(self):
        r = self.login_otp(self.client_for_device(IPHONE))
        raw = r.cookies["sa_session"].value
        s = UserSession.objects.get()
        self.assertNotEqual(s.token_hash, raw)
        self.assertEqual(len(s.token_hash), 64)
        d = Device.objects.get()
        self.assertEqual(d.device_type, "mobile")
        self.assertIn("Safari", d.browser)
        self.assertEqual(r.json()["session"]["device"]["device_type"], "mobile")

    def test_same_device_relogin_reuses_device_record(self):
        a = self.client_for_device(MAC)
        self.login_otp(a)
        self.login_otp(a)
        self.assertEqual(Device.objects.count(), 1)
        self.assertEqual(UserSession.objects.count(), 2)
        self.assertEqual(UserSession.objects.filter(active_slot=1).count(), 1)

    def test_protected_endpoints_require_session(self):
        c = self.client_for_device()
        for path in ["/me", "/security/settings"]:
            r = c.get(f"{API}{path}")
            self.assertEqual(r.status_code, 401)
            self.assertEqual(r.json()["error"]["code"], "NOT_AUTHENTICATED")
        self.assertEqual(c.post(f"{API}/webauthn/register/options", {}, format="json").status_code, 401)

    def test_csrf_enforced_on_unsafe_methods(self):
        c = self.client_for_device(MAC, csrf=True)
        csrf = c.get(f"{API}/auth/csrf").json()["csrf_token"]
        blocked = c.post(f"{API}/auth/otp/request", {"identifier": "alice@example.com"}, format="json")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["error"]["code"], "CSRF_FAILED")
        ok = c.post(f"{API}/auth/otp/request", {"identifier": "alice@example.com"}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(ok.status_code, 202)

    def test_security_settings_payload(self):
        a = self.client_for_device(MAC)
        self.login_otp(a)
        data = a.get(f"{API}/security/settings").json()
        self.assertEqual(data["policy"]["lockout_minutes"], 60)
        self.assertTrue(data["devices"][0]["is_current"])
        self.assertTrue(data["devices"][0]["is_active"])
        self.assertTrue(data["recent_activity"][0]["success"])
