"""
Server-side session management with the one-active-device policy.

Policy: a successful login on a new device REVOKES the previous active session first, then grants
the new one. Both steps happen in one transaction while holding a row lock on the user, and the
UNIQUE(user, active_slot) constraint is the final guarantee at the database level.
"""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from user_agents import parse as parse_ua

from accounts.models import User
from core.crypto import random_token, sha256_hex
from core.utils import get_client_ip, get_user_agent

from .models import Device, UserSession


def describe_device(user_agent: str) -> dict:
    ua = parse_ua(user_agent or "")
    if ua.is_tablet:
        kind = "tablet"
    elif ua.is_mobile:
        kind = "mobile"
    elif ua.is_pc:
        kind = "desktop"
    else:
        kind = "other"
    browser = (ua.browser.family or "Unknown browser")[:60]
    os_name = (ua.os.family or "Unknown OS")[:60]
    return {"device_type": kind, "browser": browser, "os": os_name, "label": f"{browser} on {os_name}"[:100]}


def _upsert_device(user, raw_device_token: str | None, request, now):
    info = describe_device(get_user_agent(request))
    if raw_device_token:
        device = Device.objects.filter(user=user, token_hash=sha256_hex(raw_device_token)).first()
        if device:
            for k, v in info.items():
                setattr(device, k, v)
            device.last_seen_at = now
            device.save()
            return device, raw_device_token
    raw_device_token = random_token(32)
    device = Device.objects.create(user=user, token_hash=sha256_hex(raw_device_token), last_seen_at=now, **info)
    return device, raw_device_token


def start_session(user, request, method: str):
    """
    Returns (raw_session_token, session, raw_device_token). The raw tokens are only ever handed to the
    client inside HttpOnly cookies; the database stores their SHA-256.
    """
    now = timezone.now()
    raw_device = request.COOKIES.get(settings.DEVICE_COOKIE_NAME)
    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)  # serialise concurrent logins for this user

        for old in UserSession.objects.filter(user=user, active_slot=1):
            expired = old.expires_at <= now
            old.revoked_at = now
            old.revoked_reason = UserSession.Reason.EXPIRED if expired else UserSession.Reason.REPLACED
            old.active_slot = None
            old.save(update_fields=["revoked_at", "revoked_reason", "active_slot"])

        device, raw_device = _upsert_device(user, raw_device, request, now)
        raw_token = random_token(32)
        session = UserSession.objects.create(
            user=user,
            device=device,
            token_hash=sha256_hex(raw_token),
            active_slot=1,
            auth_method=method,
            ip_address=get_client_ip(request),
            last_activity_at=now,
            expires_at=now + timedelta(seconds=settings.SESSION_ABSOLUTE_TIMEOUT_SECONDS),
        )
    return raw_token, session, raw_device


def revoke(session: UserSession, reason: str) -> None:
    UserSession.objects.filter(pk=session.pk, revoked_at__isnull=True).update(
        revoked_at=timezone.now(), revoked_reason=reason, active_slot=None
    )


def set_session_cookies(response, raw_token: str, raw_device: str):
    common = {"secure": settings.COOKIE_SECURE, "httponly": True, "samesite": settings.COOKIE_SAMESITE, "path": "/"}
    response.set_cookie(
        settings.SESSION_COOKIE_NAME_AUTH, raw_token, max_age=settings.SESSION_ABSOLUTE_TIMEOUT_SECONDS, **common
    )
    response.set_cookie(settings.DEVICE_COOKIE_NAME, raw_device, max_age=60 * 60 * 24 * 365, **common)


def clear_session_cookie(response):
    response.delete_cookie(settings.SESSION_COOKIE_NAME_AUTH, path="/", samesite=settings.COOKIE_SAMESITE)
