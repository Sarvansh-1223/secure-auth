from django.conf import settings
from django.db import models


class OTPVerification(models.Model):
    class Purpose(models.TextChoices):
        REGISTER = "REGISTER"
        LOGIN = "LOGIN"

    class Channel(models.TextChoices):
        EMAIL = "EMAIL"
        SMS = "SMS"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    purpose = models.CharField(max_length=10, choices=Purpose.choices)
    channel = models.CharField(max_length=5, choices=Channel.choices)
    # The code itself is never stored: HMAC-SHA256(pepper, salt, code).
    salt = models.CharField(max_length=32)
    code_hmac = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_verification"
        indexes = [
            models.Index(
                fields=["user", "purpose", "consumed_at", "expires_at"], name="otp_lookup_idx"
            )
        ]
