from rest_framework.response import Response

from accounts.identifiers import find_user, parse_identifier
from accounts.serializers import CodeSerializer, IdentifierSerializer
from core.utils import get_client_ip
from core.views import PublicAPIView
from security import lockout
from security.flow import verify_code_flow
from sessions_app.login import complete_login

from . import services
from .models import OTPVerification

LOGIN = OTPVerification.Purpose.LOGIN
GENERIC = "If the account exists, we've sent a six-digit code."


class OtpRequestView(PublicAPIView):
    """Send (or re-send) a login code. Response is identical for registered and unknown identifiers."""

    throttle_scope = "otp_request"

    def post(self, request):
        s = IdentifierSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ident = parse_identifier(s.validated_data["identifier"])
        user = find_user(ident)
        known = user is not None and user.is_active

        lockout.guard(user if known else None, ident.digest, get_client_ip(request))  # 423 while locked
        services.check_send_allowed(ident.digest, LOGIN)                               # 429 cooldown / hourly cap

        if known and user.is_identifier_verified(ident.kind):
            services.issue_and_send(user, LOGIN, ident.kind)

        from django.conf import settings

        return Response(
            {
                "message": GENERIC,
                "expires_in_seconds": settings.OTP_TTL_SECONDS,
                "resend_after_seconds": settings.OTP_RESEND_COOLDOWN_SECONDS,
            },
            status=202,
        )


class OtpVerifyView(PublicAPIView):
    throttle_scope = "credential_check"

    def post(self, request):
        s = CodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user, _ = verify_code_flow(request, s.validated_data["identifier"], s.validated_data["code"], "LOGIN")
        return complete_login(request, user, "OTP")
