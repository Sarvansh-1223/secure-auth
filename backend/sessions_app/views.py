from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserSession
from .services import clear_session_cookie, revoke


class LogoutView(APIView):
    """Invalidates the active session server-side (the cookie alone is worthless afterwards)."""

    def post(self, request):
        revoke(request.auth, UserSession.Reason.LOGOUT)
        response = Response({"message": "Signed out."})
        clear_session_cookie(response)
        return response
