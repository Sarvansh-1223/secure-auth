from rest_framework.response import Response

from accounts.presenters import session_payload, user_payload
from webauthn_app.models import BiometricCredential

from .services import set_session_cookies, start_session


def complete_login(request, user, method: str, status=200) -> Response:
    """Final step of every successful authentication: swap the active session and set cookies."""
    raw_token, session, raw_device = start_session(user, request, method)
    enrolled = BiometricCredential.objects.filter(user=user, revoked_at__isnull=True).exists()
    response = Response(
        {"user": user_payload(user), "session": session_payload(session), "biometric_enrolled": enrolled},
        status=status,
    )
    set_session_cookies(response, raw_token, raw_device)
    return response
