from django.http import JsonResponse
from django.middleware.csrf import get_token
from rest_framework.permissions import SAFE_METHODS, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .csrf import enforce_csrf


class PublicAPIView(APIView):
    """
    Base for unauthenticated endpoints. They still require a valid CSRF token on unsafe
    methods (login CSRF / forced-login attacks are real), so CSRF is enforced explicitly.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        if request.method not in SAFE_METHODS:
            enforce_csrf(request)
        super().initial(request, *args, **kwargs)


class CsrfView(PublicAPIView):
    """GET /auth/csrf - sets the CSRF cookie and returns the token for the X-CSRFToken header."""

    def get(self, request):
        return Response({"csrf_token": get_token(request._request)})


class HealthView(PublicAPIView):
    def get(self, request):
        return Response({"status": "ok"})


def _error(status, code, message):
    return JsonResponse({"error": {"code": code, "message": message, "details": {}}}, status=status)


def not_found(request, exception=None):
    return _error(404, "NOT_FOUND", "Not found.")


def server_error(request):
    return _error(500, "SERVER_ERROR", "Something went wrong.")
