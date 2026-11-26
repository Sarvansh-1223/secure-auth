from django.conf import settings
from django.db import models


class BiometricCredential(models.Model):
    """A WebAuthn credential. Only the PUBLIC key is stored; biometric data never leaves the device."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credentials")
    device = models.ForeignKey("sessions_app.Device", null=True, blank=True, on_delete=models.SET_NULL, related_name="credentials")
    credential_id = models.CharField(max_length=512, unique=True)  # base64url
    public_key = models.BinaryField()  # COSE-encoded
    sign_count = models.BigIntegerField(default=0)
    attachment = models.CharField(max_length=20, blank=True)  # platform | cross-platform
    transports = models.JSONField(default=list, blank=True)
    nickname = models.CharField(max_length=100, blank=True)
    backed_up = models.BooleanField(default=False)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "biometric_credential"
        indexes = [models.Index(fields=["user", "revoked_at"], name="cred_user_rev_idx")]


class WebAuthnChallenge(models.Model):
    """Single-use, short-lived server-side challenges (replay protection, works across workers)."""

    class Purpose(models.TextChoices):
        REGISTER = "REGISTER"
        AUTHENTICATE = "AUTHENTICATE"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="webauthn_challenges")
    identifier_hash = models.CharField(max_length=64, blank=True)
    challenge_hash = models.CharField(max_length=64, unique=True)
    challenge = models.BinaryField()
    purpose = models.CharField(max_length=12, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "webauthn_challenge"
        indexes = [models.Index(fields=["expires_at"], name="challenge_exp_idx")]
