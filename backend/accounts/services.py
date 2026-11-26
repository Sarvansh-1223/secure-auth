"""Registration: duplicate-safe, enumeration-safe (callers always answer 202 with the same body)."""
from django.db import IntegrityError, transaction

from core.exceptions import ResendThrottled
from otp import delivery, services as otp_services
from otp.models import OTPVerification

from .models import User, UserProfile

REGISTER = OTPVerification.Purpose.REGISTER


def _field(kind: str) -> str:
    return "email" if kind == "email" else "phone_e164"


def register(identifier, surname: str, date_of_birth) -> None:
    """
    * New identifier           -> create unverified user + profile, send verification code.
    * Existing, UNverified     -> (abandoned signup) refresh profile, send a new code.
    * Existing, verified       -> create nothing; tell the owner via a notice. No duplicate possible
                                  (UNIQUE constraints + IntegrityError handling for races).
    Resend cooldown applies silently so the HTTP response never differs.
    """
    kind, value = identifier.kind, identifier.value
    try:
        otp_services.check_send_allowed(identifier.digest, REGISTER)
    except ResendThrottled:
        return

    user = User.objects.filter(**{_field(kind): value}).first()
    if user is None:
        try:
            with transaction.atomic():
                user = User.objects.create_user(**{_field(kind): value})
                UserProfile.objects.create(user=user, surname=surname, date_of_birth=date_of_birth)
        except IntegrityError:  # lost a race with a concurrent registration of the same identifier
            user = User.objects.filter(**{_field(kind): value}).first()
            if user is None:
                return

    if user.is_identifier_verified(kind):
        delivery.send_notice(
            email=user.email if kind == "email" else None,
            phone=user.phone_e164 if kind == "phone" else None,
            text="Someone tried to register with this address, but you already have an account. "
            "Sign in instead. If this wasn't you, no action is needed.",
        )
        return

    UserProfile.objects.filter(user=user).update(surname=surname, date_of_birth=date_of_birth)
    otp_services.issue_and_send(user, REGISTER, kind)


def mark_verified(user, kind: str) -> None:
    field = "email_verified" if kind == "email" else "phone_verified"
    if not getattr(user, field):
        setattr(user, field, True)
        user.save(update_fields=[field, "updated_at"])
