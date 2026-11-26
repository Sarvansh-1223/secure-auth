from django.conf import settings
from django.db import models


class Device(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    token_hash = models.CharField(max_length=64)  # SHA-256 of the long-lived device cookie
    label = models.CharField(max_length=100)
    device_type = models.CharField(max_length=20)  # desktop | mobile | tablet | other
    browser = models.CharField(max_length=60, blank=True)
    os = models.CharField(max_length=60, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device"
        constraints = [models.UniqueConstraint(fields=["user", "token_hash"], name="uniq_device_per_user")]
        indexes = [models.Index(fields=["user", "last_seen_at"], name="device_user_seen_idx")]


class UserSession(models.Model):
    class Reason(models.TextChoices):
        LOGOUT = "LOGOUT"
        REPLACED = "REPLACED"
        EXPIRED = "EXPIRED"
        REVOKED = "REVOKED"

    class Method(models.TextChoices):
        OTP = "OTP"
        WEBAUTHN = "WEBAUTHN"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="sessions")
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256; the raw token only lives in the cookie
    # 1 while active, NULL once revoked. UNIQUE(user, active_slot) lets the DATABASE guarantee at most
    # one active session per user (MySQL has no partial unique indexes; NULLs never collide).
    active_slot = models.PositiveSmallIntegerField(null=True, blank=True, default=1)
    auth_method = models.CharField(max_length=10, choices=Method.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=10, choices=Reason.choices, blank=True)

    class Meta:
        db_table = "user_session"
        constraints = [models.UniqueConstraint(fields=["user", "active_slot"], name="one_active_session_per_user")]
        indexes = [models.Index(fields=["user", "revoked_at"], name="session_user_rev_idx")]
