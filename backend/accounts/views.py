from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import ResendThrottled
from core.views import PublicAPIView
from otp import services as otp_services
from otp.models import OTPVerification
from security.flow import verify_code_flow
from sessions_app.login import complete_login

from . import services
from .identifiers import Identifier, find_user, parse_identifier
from .presenters import user_payload
from .serializers import CodeSerializer, IdentifierSerializer, RegisterSerializer

REGISTER = OTPVerification.Purpose.REGISTER
GENERIC_REGISTER_MESSAGE = (
    "If the details are valid, we've sent a verification code. Enter it to finish creating your account."
)


class RegisterView(PublicAPIView):
    throttle_scope = "register"

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        ident = Identifier("email", d["email"]) if d.get("email") else Identifier("phone", d["phone"])
        services.register(ident, d["surname"], d["date_of_birth"])
        # Identical response whether the identifier is new, pending, or already registered.
        return Response(
            {"message": GENERIC_REGISTER_MESSAGE, "identifier": ident.value, "channel": ident.kind},
            status=202,
        )


class RegisterResendView(PublicAPIView):
    throttle_scope = "otp_request"

    def post(self, request):
        s = IdentifierSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ident = parse_identifier(s.validated_data["identifier"])
        otp_services.check_send_allowed(ident.digest, REGISTER)  # may raise ResendThrottled (429)
        user = find_user(ident)
        if user and user.is_active and not user.is_identifier_verified(ident.kind):
            otp_services.issue_and_send(user, REGISTER, ident.kind)
        return Response({"message": "If a verification is pending, a new code has been sent."}, status=202)


class RegisterVerifyView(PublicAPIView):
    throttle_scope = "credential_check"

    def post(self, request):
        s = CodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user, ident = verify_code_flow(request, s.validated_data["identifier"], s.validated_data["code"], "REGISTER")
        services.mark_verified(user, ident.kind)
        return complete_login(request, user, "OTP")


class MeView(APIView):
    def get(self, request):
        from accounts.presenters import session_payload

        return Response({"user": user_payload(request.user), "session": session_payload(request.auth)})
