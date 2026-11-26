from django.conf import settings
from django.db import models
from django.db.models import Q


class LoginAttempt(models.Model):
    class Method(models.TextChoices):
        OTP = "OTP"
        WEBAUTHN = "WEBAUTHN"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="login_attempts")
    identifier_hash = models.CharField(max_length=64)
    method = models.CharField(max_length=10, choices=Method.choices)
    success = models.BooleanField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    failure_reason = models.CharField(max_length=40, blank=True)  # internal only, never sent to clients
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "login_attempt"
        indexes = [
            models.Index(fields=["identifier_hash", "created_at"], name="attempt_ident_idx"),
            models.Index(fields=["ip_address", "created_at"], name="attempt_ip_idx"),
            models.Index(fields=["user", "created_at"], name="attempt_user_idx"),
        ]


class AccountLockout(models.Model):
    """
    Consecutive-failure counter + lock timestamp.

    Keyed by ``user`` for real accounts. For identifiers that don't belong to any account the row
    is keyed by ``identifier_hash`` instead, so locking behaves identically and cannot be used to
    discover which identifiers are registered.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="lockout")
    identifier_hash = models.CharField(max_length=64, null=True, blank=True, unique=True)
    consecutive_failures = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "account_lockout"
        constraints = [
            models.CheckConstraint(
                condition=(Q(user__isnull=False) & Q(identifier_hash__isnull=True))
                | (Q(user__isnull=True) & Q(identifier_hash__isnull=False)),
                name="lockout_exactly_one_subject",
            )
        ]
