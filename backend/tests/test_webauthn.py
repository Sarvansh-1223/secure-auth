from security.models import AccountLockout
from sessions_app.models import UserSession
from tests.base import API, AuthTestCase
from tests.webauthn_sim import SoftAuthenticator
from webauthn_app.models import BiometricCredential, WebAuthnChallenge


class WebAuthnTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("alice@example.com")
        self.dev = self.client_for_device()
        self.login_otp(self.dev)
        self.auth = SoftAuthenticator()

    def enroll(self):
        opts = self.dev.post(f"{API}/webauthn/register/options", {"attachment": "platform"}, format="json")
        self.assertEqual(opts.status_code, 200, opts.content)
        options = opts.json()["options"]
        self.assertEqual(options["authenticatorSelection"]["userVerification"], "required")
        cred = self.auth.create(options)
        return self.dev.post(f"{API}/webauthn/register/verify", {"credential": cred, "nickname": "My Mac", "attachment": "platform"}, format="json")

    def auth_options(self, client, identifier="alice@example.com"):
        r = client.post(f"{API}/webauthn/authenticate/options", {"identifier": identifier}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["options"]

    def test_registration_requires_authentication(self):
        anon = self.client_for_device()
        self.assertEqual(anon.post(f"{API}/webauthn/register/options", {}, format="json").status_code, 401)

    def test_enroll_then_authenticate_end_to_end(self):
        r = self.enroll()
        self.assertEqual(r.status_code, 201, r.content)
        stored = BiometricCredential.objects.get()
        self.assertEqual(stored.nickname, "My Mac")
        self.assertTrue(len(bytes(stored.public_key)) > 32)  # public key only

        new_device = self.client_for_device("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36")
        options = self.auth_options(new_device)
        self.assertEqual(len(options["allowCredentials"]), 1)
        res = new_device.post(f"{API}/webauthn/authenticate/verify", {"credential": self.auth.get(options)}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["session"]["auth_method"], "WEBAUTHN")

        # single-device policy applies to biometric logins too
        self.assertEqual(self.dev.get(f"{API}/me").json()["error"]["code"], "SESSION_REPLACED")
        self.assertEqual(new_device.get(f"{API}/me").status_code, 200)
        self.assertEqual(UserSession.objects.filter(active_slot=1).count(), 1)
        self.assertEqual(BiometricCredential.objects.get().sign_count, 1)

    def test_bad_signature_rejected_and_counts_toward_lockout(self):
        self.enroll()
        c = self.client_for_device()
        for i in range(5):
            options = self.auth_options(c) if i < 4 else None
            if options is None:
                break
            r = c.post(f"{API}/webauthn/authenticate/verify", {"credential": self.auth.get(options, tamper_signature=True)}, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json()["error"]["code"], "INVALID_CREDENTIALS")
        options = self.auth_options(c)
        r = c.post(f"{API}/webauthn/authenticate/verify", {"credential": self.auth.get(options, tamper_signature=True)}, format="json")
        self.assertEqual(r.status_code, 423)
        self.assertIsNotNone(AccountLockout.objects.get(user=self.user).locked_until)
        # OTP is blocked as well: one counter, all methods
        self.assertEqual(self.wrong_code(c).status_code, 423)

    def test_challenge_is_single_use(self):
        self.enroll()
        c = self.client_for_device()
        options = self.auth_options(c)
        assertion = self.auth.get(options)
        self.assertEqual(c.post(f"{API}/webauthn/authenticate/verify", {"credential": assertion}, format="json").status_code, 200)
        replay = self.client_for_device().post(f"{API}/webauthn/authenticate/verify", {"credential": assertion}, format="json")
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(WebAuthnChallenge.objects.count(), 0)

    def test_wrong_origin_rejected(self):
        self.enroll()
        c = self.client_for_device()
        options = self.auth_options(c)
        r = c.post(f"{API}/webauthn/authenticate/verify", {"credential": self.auth.get(options, origin="https://evil.example")}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_other_users_credential_cannot_be_used(self):
        self.enroll()
        self.make_user("mallory@example.com")
        c = self.client_for_device()
        options = self.auth_options(c, "mallory@example.com")  # decoy options (no credentials)
        r = c.post(f"{API}/webauthn/authenticate/verify", {"credential": self.auth.get(options)}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_unknown_identifier_gets_same_shaped_options(self):
        c = self.client_for_device()
        known_no_cred = self.auth_options(c, "alice@example.com")
        unknown = self.auth_options(c, "nobody@example.com")
        self.assertEqual(set(known_no_cred), set(unknown))
        self.assertEqual(len(unknown["allowCredentials"]), 1)

    def test_remove_credential(self):
        self.enroll()
        cred = BiometricCredential.objects.get()
        self.assertEqual(self.dev.delete(f"{API}/security/credentials/{cred.id}").status_code, 204)
        c = self.client_for_device()
        options = self.auth_options(c)
        r = c.post(f"{API}/webauthn/authenticate/verify", {"credential": self.auth.get(options)}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_duplicate_credential_rejected(self):
        self.assertEqual(self.enroll().status_code, 201)
        opts = self.dev.post(f"{API}/webauthn/register/options", {"attachment": "platform"}, format="json").json()["options"]
        self.assertEqual(len(opts["excludeCredentials"]), 1)
        r = self.dev.post(f"{API}/webauthn/register/verify", {"credential": self.auth.create(opts)}, format="json")
        self.assertEqual(r.status_code, 400)
