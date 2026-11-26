from datetime import timedelta

from django.utils import timezone

from security.models import AccountLockout, LoginAttempt
from tests.base import API, AuthTestCase


class LockoutTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("alice@example.com", phone="+14155552671")
        self.device_a = self.client_for_device()

    def fail_n(self, n, client=None, identifier="alice@example.com"):
        out = []
        for _ in range(n):
            out.append((client or self.device_a).post(f"{API}/auth/otp/verify", {"identifier": identifier, "code": "000000"}, format="json"))
        return out

    def test_five_failures_lock_for_one_hour(self):
        self.request_code(self.device_a, "alice@example.com")
        results = self.fail_n(5)
        self.assertEqual([r.status_code for r in results[:4]], [400] * 4)
        self.assertEqual([r.json()["error"]["details"]["remaining_attempts"] for r in results[:4]], [4, 3, 2, 1])
        last = results[4]
        self.assertEqual(last.status_code, 423)
        body = last.json()["error"]
        self.assertEqual(body["code"], "ACCOUNT_LOCKED")
        self.assertEqual(body["details"]["retry_after_seconds"], 3600)

        lock = AccountLockout.objects.get(user=self.user)
        self.assertIsNotNone(lock.locked_until)
        self.assertAlmostEqual((lock.locked_until - timezone.now()).total_seconds(), 3600, delta=5)

    def test_locked_account_rejects_even_correct_code_and_other_methods(self):
        self.request_code(self.device_a, "alice@example.com")
        good = self.last_code()
        self.fail_n(5)
        r = self.device_a.post(f"{API}/auth/otp/verify", {"identifier": "alice@example.com", "code": good}, format="json")
        self.assertEqual(r.status_code, 423)
        # requesting a code and WebAuthn options are refused too
        self.assertEqual(self.device_a.post(f"{API}/auth/otp/request", {"identifier": "alice@example.com"}, format="json").status_code, 423)
        self.assertEqual(self.device_a.post(f"{API}/webauthn/authenticate/options", {"identifier": "alice@example.com"}, format="json").status_code, 423)

    def test_lock_cannot_be_bypassed_by_other_device_or_other_identifier(self):
        self.fail_n(5)
        other_device = self.client_for_device("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148 Safari/604.1")
        self.assertEqual(self.fail_n(1, other_device)[0].status_code, 423)
        # the same account through its phone number shares the counter
        self.assertEqual(self.fail_n(1, other_device, "+14155552671")[0].status_code, 423)

    def test_lockout_status_endpoint(self):
        s = self.device_a.get(f"{API}/auth/lockout-status", {"identifier": "alice@example.com"}).json()
        self.assertFalse(s["locked"])
        self.fail_n(5)
        s = self.device_a.get(f"{API}/auth/lockout-status", {"identifier": "alice@example.com"}).json()
        self.assertTrue(s["locked"])
        self.assertTrue(3590 <= s["retry_after_seconds"] <= 3601)

    def test_lock_expires_after_one_hour_and_counter_resets(self):
        self.fail_n(5)
        AccountLockout.objects.update(locked_until=timezone.now() - timedelta(seconds=1))
        self.request_code(self.device_a, "alice@example.com")
        r = self.device_a.post(f"{API}/auth/otp/verify", {"identifier": "alice@example.com", "code": self.last_code()}, format="json")
        self.assertEqual(r.status_code, 200)
        lock = AccountLockout.objects.get(user=self.user)
        self.assertEqual(lock.consecutive_failures, 0)
        self.assertIsNone(lock.locked_until)

    def test_success_resets_consecutive_counter(self):
        self.request_code(self.device_a, "alice@example.com")
        code = self.last_code()
        self.fail_n(4)
        self.assertEqual(AccountLockout.objects.get(user=self.user).consecutive_failures, 4)
        ok = self.device_a.post(f"{API}/auth/otp/verify", {"identifier": "alice@example.com", "code": code}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(AccountLockout.objects.get(user=self.user).consecutive_failures, 0)
        # four more failures after the reset must NOT lock (they are not consecutive with the earlier four)
        self.assertEqual({r.status_code for r in self.fail_n(4)}, {400})

    def test_unknown_identifiers_lock_identically(self):
        results = self.fail_n(5, identifier="ghost@example.com")
        self.assertEqual([r.status_code for r in results], [400, 400, 400, 400, 423])
        self.assertEqual(self.fail_n(1, identifier="ghost@example.com")[0].status_code, 423)
        self.assertFalse(AccountLockout.objects.filter(user=self.user).exists())

    def test_failures_are_logged_for_audit(self):
        self.fail_n(2)
        self.assertEqual(LoginAttempt.objects.filter(user=self.user, success=False).count(), 2)
        self.assertNotIn("alice", "".join(LoginAttempt.objects.values_list("identifier_hash", flat=True)))
