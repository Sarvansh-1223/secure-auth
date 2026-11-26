"""
Account lockout: 5 consecutive failed credential checks => locked for exactly one hour.

Every credential verification (OTP or WebAuthn) in the code base MUST go through:

    lockout.guard(...)            # before verifying: refuses while locked
    lockout.record_success(...)   # on success: resets the counter
    raise lockout.record_failure(...)  # on failure: increments / locks, returns the exception to raise

State lives in the database (not cookies / localStorage / memory), so refreshing the page,
switching browser, or switching device cannot bypass it.
"""
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.exceptions import AccountLocked, ApiError, InvalidCredentials

from .models import AccountLockout, LoginAttempt


class IpBlocked(ApiError):
    status_code = 429
    code = "RATE_LIMITED"
    default_detail = "Too many requests. Please slow down."


def _lookup(user, digest):
    if user is not None:
        return AccountLockout.objects.filter(user=user).first()
    return AccountLockout.objects.filter(identifier_hash=digest, user__isnull=True).first()


def _lock_row(user, digest):
    """Get-or-create the row and lock it for the rest of the transaction."""
    kwargs = {"user": user} if user is not None else {"identifier_hash": digest}
    try:
        with transaction.atomic():
            row, _ = AccountLockout.objects.get_or_create(**kwargs)
    except IntegrityError:
        pass
    return AccountLockout.objects.select_for_update().get(**kwargs)


def _remaining(row, now):
    return (row.locked_until - now).total_seconds()


def status(user, digest) -> dict:
    """Lock state for the lockout-status endpoint (also lazily clears expired locks)."""
    row = _lookup(user, digest)
    now = timezone.now()
    if row and row.locked_until:
        if row.locked_until > now:
            return {"locked": True, "retry_after_seconds": int(_remaining(row, now)) + 1, "locked_until": row.locked_until}
        AccountLockout.objects.filter(pk=row.pk, locked_until=row.locked_until).update(
            locked_until=None, consecutive_failures=0
        )
    return {"locked": False}


def guard(user, digest, ip) -> None:
    """Raise AccountLocked while the lock is active; raise IpBlocked on abusive IPs."""
    now = timezone.now()
    row = _lookup(user, digest)
    if row and row.locked_until:
        if row.locked_until > now:
            raise AccountLocked(_remaining(row, now) + 0.999, row.locked_until)
        # Lock elapsed: start fresh (conditional so concurrent requests can't clobber a new lock).
        AccountLockout.objects.filter(pk=row.pk, locked_until=row.locked_until).update(
            locked_until=None, consecutive_failures=0
        )
    if ip:
        window = now - timedelta(seconds=settings.IP_FAILURE_WINDOW_SECONDS)
        failures = LoginAttempt.objects.filter(ip_address=ip, success=False, created_at__gte=window).count()
        if failures >= settings.IP_FAILURE_LIMIT:
            raise IpBlocked(details={"retry_after_seconds": settings.IP_FAILURE_WINDOW_SECONDS})


def record_success(user, digest, method, ip, user_agent) -> None:
    with transaction.atomic():
        row = _lock_row(user, digest)
        row.consecutive_failures = 0
        row.locked_until = None
        row.save(update_fields=["consecutive_failures", "locked_until", "updated_at"])
        LoginAttempt.objects.create(
            user=user, identifier_hash=digest, method=method, success=True, ip_address=ip, user_agent=user_agent
        )


def record_failure(user, digest, method, ip, user_agent, reason="invalid_credential") -> ApiError:
    """Count the failure; returns AccountLocked (5th failure) or InvalidCredentials to raise."""
    now = timezone.now()
    with transaction.atomic():
        row = _lock_row(user, digest)
        if row.locked_until and row.locked_until > now:  # lost a race with another failing request
            return AccountLocked(_remaining(row, now) + 0.999, row.locked_until)

        row.consecutive_failures += 1
        row.last_failure_at = now
        locked = row.consecutive_failures >= settings.LOCKOUT_MAX_FAILURES
        if locked:
            row.locked_until = now + timedelta(seconds=settings.LOCKOUT_DURATION_SECONDS)
        row.save(update_fields=["consecutive_failures", "last_failure_at", "locked_until", "updated_at"])
        LoginAttempt.objects.create(
            user=user,
            identifier_hash=digest,
            method=method,
            success=False,
            ip_address=ip,
            user_agent=user_agent,
            failure_reason=reason,
        )

    if locked:
        return AccountLocked(settings.LOCKOUT_DURATION_SECONDS, row.locked_until)
    exc = InvalidCredentials()
    exc.details = {"remaining_attempts": settings.LOCKOUT_MAX_FAILURES - row.consecutive_failures}
    return exc
