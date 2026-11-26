from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.identifiers import find_user, parse_identifier
from accounts.serializers import IdentifierSerializer
from core.exceptions import ApiError
from core.views import PublicAPIView
from sessions_app.models import Device, UserSession
from webauthn_app.models import BiometricCredential

from . import lockout
from .models import LoginAttempt


class LockoutStatusView(PublicAPIView):
    """
    GET /auth/lockout-status?identifier=...
    Same shape for every identifier. A lock can only exist after 5 failed attempts, and unknown
    identifiers are locked the same way, so this endpoint is not an account-existence oracle.
    """

    throttle_scope = "status"

    def get(self, request):
        s = IdentifierSerializer(data={"identifier": request.query_params.get("identifier", "")})
        s.is_valid(raise_exception=True)
        ident = parse_identifier(s.validated_data["identifier"])
        user = find_user(ident)
        st = lockout.status(user if user and user.is_active else None, ident.digest)
        if st["locked"]:
            return Response(
                {"locked": True, "retry_after_seconds": st["retry_after_seconds"], "locked_until": st["locked_until"].isoformat()}
            )
        return Response({"locked": False, "retry_after_seconds": 0, "locked_until": None})


class SecuritySettingsView(APIView):
    def get(self, request):
        user, current = request.user, request.auth

        devices = []
        active = {s.device_id: s for s in UserSession.objects.filter(user=user, revoked_at__isnull=True)}
        for d in Device.objects.filter(user=user).order_by("-last_seen_at")[:20]:
            devices.append(
                {
                    "id": d.id, "label": d.label, "device_type": d.device_type, "browser": d.browser, "os": d.os,
                    "first_seen_at": d.first_seen_at.isoformat(), "last_seen_at": d.last_seen_at.isoformat(),
                    "is_active": d.id in active, "is_current": d.id == current.device_id,
                }
            )

        credentials = [
            {
                "id": c.id, "nickname": c.nickname, "attachment": c.attachment, "backed_up": c.backed_up,
                "created_at": c.created_at.isoformat(),
                "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
            }
            for c in BiometricCredential.objects.filter(user=user, revoked_at__isnull=True).order_by("-created_at")
        ]

        recent = [
            {"method": a.method, "success": a.success, "ip_address": a.ip_address, "at": a.created_at.isoformat()}
            for a in LoginAttempt.objects.filter(user=user).order_by("-created_at")[:10]
        ]

        return Response(
            {
                "policy": {
                    "single_active_device": True,
                    "lockout_after_failures": 5,
                    "lockout_minutes": 60,
                },
                "current_session": {
                    "started_at": current.created_at.isoformat(),
                    "expires_at": current.expires_at.isoformat(),
                    "auth_method": current.auth_method,
                },
                "devices": devices,
                "credentials": credentials,
                "recent_activity": recent,
            }
        )


class CredentialDetailView(APIView):
    def delete(self, request, pk):
        updated = BiometricCredential.objects.filter(pk=pk, user=request.user, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )
        if not updated:
            raise ApiError("Not found.", code="NOT_FOUND")
        return Response(status=204)
