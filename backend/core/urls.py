from django.urls import include, path

from .views import CsrfView, HealthView

urlpatterns = [
    path("health", HealthView.as_view()),
    path("auth/csrf", CsrfView.as_view(), name="csrf"),
    path("", include("accounts.urls")),
    path("", include("otp.urls")),
    path("", include("webauthn_app.urls")),
    path("", include("security.urls")),
    path("", include("sessions_app.urls")),
]
