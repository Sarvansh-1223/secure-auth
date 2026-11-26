"""
One-time-password lifecycle.

* Codes come from ``secrets`` (CSPRNG) and are stored only as a salted HMAC.
* A fresh code invalidates earlier unconsumed codes of the same purpose.
* Verification is constant-time, attempt-capped per code, and consumes the code with an
  atomic conditional UPDATE so a code can never be redeemed twice (replay / race safe).
* Resend cooldown + hourly send cap are keyed by the *identifier digest* (not the user),
  so they behave identically for registered and unknown identifiers.
"""
import logging
import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from core.crypto import constant_time_equal, hmac_hex, random_digits, random_token
from core.exceptions import ResendThrottled

from . import delivery
from .models import OTPVerification

logger = logging.getLogger(__name__)

_CODE_CHARS = set("0123456789")


def _channel_for(kind: str) -> str:
    return OTPVerification.Channel.EMAIL if kind == "email" else OTPVerification.Channel.SMS


def check_send_allowed(digest: str, purpose: str) -> None:
    """Enforce resend cooldown and hourly cap. Raises ResendThrottled. Consumes one send slot."""
    now = time.time()
    cooldown = settings.OTP_RESEND_COOLDOWN_SECONDS
    cd_key = f"otp:cooldown:{purpose}:{digest}"
    if not cache.add(cd_key, now, cooldown):
        started = cache.get(cd_key) or now
        raise ResendThrottled(started + cooldown - now)

    hr_key = f"otp:hourly:{purpose}:{digest}"
    cache.add(hr_key, 0, 3600)
    try:
        count = cache.incr(hr_key)
    except ValueError:  # key expired between add and incr
        cache.set(hr_key, 1, 3600)
        count = 1
    if count > settings.OTP_MAX_SENDS_PER_HOUR:
        cache.delete(cd_key)
        raise ResendThrottled(3600)


def _hash_code(salt: str, code: str) -> str:
    return hmac_hex("otp", salt, code)


@transaction.atomic
def issue(user, purpose: str, kind: str) -> str:
    """Create a new code (invalidating older ones) and return the plaintext for delivery only."""
    now = timezone.now()
    OTPVerification.objects.filter(
        user=user, purpose=purpose, consumed_at__isnull=True
    ).update(consumed_at=now)  # supersede

    code = random_digits(settings.OTP_LENGTH)
    salt = random_token(12)[:16]
    OTPVerification.objects.create(
        user=user,
        purpose=purpose,
        channel=_channel_for(kind),
        salt=salt,
        code_hmac=_hash_code(salt, code),
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
        last_sent_at=now,
    )
    return code


def issue_and_send(user, purpose: str, kind: str) -> None:
    code = issue(user, purpose, kind)
    try:
        delivery.deliver_code(
            channel=_channel_for(kind),
            email=user.email,
            phone=user.phone_e164,
            code=code,
            purpose=purpose,
        )
    except Exception:
        # Never leak delivery failures (would differentiate real vs. unknown accounts).
        logger.exception("OTP delivery failed")


def verify_dummy(code: str) -> None:
    """Equalise work for identifiers with no live account (timing parity)."""
    constant_time_equal(_hash_code("0" * 16, (code or "")[:16]), "0" * 64)


def verify(user, purpose: str, code: str) -> bool:
    """
    True only if ``code`` matches the newest live code for (user, purpose); the code is then
    consumed atomically. Wrong guesses count against the per-code attempt cap.
    """
    code = (code or "").strip()
    well_formed = len(code) == settings.OTP_LENGTH and set(code) <= _CODE_CHARS
    now = timezone.now()

    with transaction.atomic():
        otp = (
            OTPVerification.objects.select_for_update()
            .filter(user=user, purpose=purpose, consumed_at__isnull=True, expires_at__gt=now)
            .order_by("-created_at")
            .first()
        )
        if otp is None:
            # Burn comparable CPU so "no live code" isn't distinguishable by timing.
            constant_time_equal(_hash_code("0" * 16, code), "0" * 64)
            return False

        if otp.attempts >= settings.OTP_MAX_ATTEMPTS_PER_CODE:
            OTPVerification.objects.filter(pk=otp.pk).update(consumed_at=now)
            return False

        matches = well_formed and constant_time_equal(_hash_code(otp.salt, code), otp.code_hmac)
        if not matches:
            OTPVerification.objects.filter(pk=otp.pk).update(attempts=otp.attempts + 1)
            return False

        consumed = OTPVerification.objects.filter(pk=otp.pk, consumed_at__isnull=True).update(consumed_at=now)
        return consumed == 1
