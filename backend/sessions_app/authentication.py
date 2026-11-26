from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import SAFE_METHODS

from core.crypto import sha256_hex
from core.csrf import enforce_csrf
from core.exceptions import SessionEnded, SessionExpired, SessionInvalid, SessionReplaced

from .models import UserSession
from .services import revoke


class ServerSessionAuthentication(BaseAuthentication):
    """
    Resolves the opaque session cookie against the database on EVERY request. There is no stateless
    token, so revoking a session (new login elsewhere, logout, expiry) takes effect immediately.
    """

    def authenticate(self, request):
        raw = request.COOKIES.get(settings.SESSION_COOKIE_NAME_AUTH)
        if not raw:
            return None  # -> NotAuthenticated (401) from the permission layer

        session = (
            UserSession.objects.select_related("user", "device")
            .filter(token_hash=sha256_hex(raw))
            .first()
        )
        if session is None:
            raise SessionInvalid()

        now = timezone.now()
        if session.revoked_at is not None:
            if session.revoked_reason == UserSession.Reason.REPLACED:
                err = SessionReplaced()
                err.details = {"replaced_at": session.revoked_at.isoformat()}
                raise err
            if session.revoked_reason == UserSession.Reason.EXPIRED:
                raise SessionExpired()
            raise SessionEnded()

        idle_limit = session.last_activity_at + timedelta(seconds=settings.SESSION_IDLE_TIMEOUT_SECONDS)
        if session.expires_at <= now or idle_limit <= now:
            revoke(session, UserSession.Reason.EXPIRED)
            raise SessionExpired()

        if not session.user.is_active:
            revoke(session, UserSession.Reason.REVOKED)
            raise SessionEnded()

        if request.method not in SAFE_METHODS:
            enforce_csrf(request)

        if (now - session.last_activity_at).total_seconds() >= settings.SESSION_TOUCH_INTERVAL_SECONDS:
            UserSession.objects.filter(pk=session.pk, revoked_at__isnull=True).update(last_activity_at=now)
            session.device.__class__.objects.filter(pk=session.device_id).update(last_seen_at=now)

        return session.user, session

    def authenticate_header(self, request):
        return 'Cookie realm="api"'
