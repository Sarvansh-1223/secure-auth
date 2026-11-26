from django.urls import path

from . import views

urlpatterns = [
    path("auth/register", views.RegisterView.as_view(), name="register"),
    path("auth/register/resend", views.RegisterResendView.as_view(), name="register-resend"),
    path("auth/register/verify", views.RegisterVerifyView.as_view(), name="register-verify"),
    path("me", views.MeView.as_view(), name="me"),
]
