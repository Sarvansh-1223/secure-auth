from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.identifiers import find_user, parse_identifier
from accounts.serializers import IdentifierSerializer
from core.utils import get_client_ip, get_user_agent
from core.views import PublicAPIView
from sessions_app.login import complete_login

from . import services


class RegisterOptionsSerializer(serializers.Serializer):
    attachment = serializers.ChoiceField(choices=["platform", "cross-platform"], default="platform")


class RegisterVerifySerializer(serializers.Serializer):
    credential = serializers.DictField()
    nickname = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    attachment = serializers.ChoiceField(choices=["platform", "cross-platform"], default="platform")


class CredentialSerializer(serializers.Serializer):
    credential = serializers.DictField()


class RegisterOptionsView(APIView):
    """Requires an authenticated session: biometrics can only be enrolled after a successful login."""

    throttle_scope = "webauthn"

    def post(self, request):
        s = RegisterOptionsSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response({"options": services.begin_registration(request.user, s.validated_data["attachment"])})


class RegisterVerifyView(APIView):
    throttle_scope = "webauthn"

    def post(self, request):
        s = RegisterVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        cred = services.finish_registration(
            request.user, d["credential"], d["nickname"], d["attachment"], request.auth.device
        )
        return Response(
            {"credential": {"id": cred.id, "nickname": cred.nickname, "attachment": cred.attachment,
                            "created_at": cred.created_at.isoformat()}},
            status=201,
        )


class AuthenticateOptionsView(PublicAPIView):
    throttle_scope = "webauthn"

    def post(self, request):
        s = IdentifierSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ident = parse_identifier(s.validated_data["identifier"])
        user = find_user(ident)
        return Response({"options": services.begin_authentication(ident, user, get_client_ip(request))})


class AuthenticateVerifyView(PublicAPIView):
    throttle_scope = "credential_check"

    def post(self, request):
        s = CredentialSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = services.finish_authentication(
            s.validated_data["credential"], get_client_ip(request), get_user_agent(request)
        )
        return complete_login(request, user, "WEBAUTHN")
