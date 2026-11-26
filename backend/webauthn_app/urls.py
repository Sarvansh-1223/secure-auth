from django.urls import path

from . import views

urlpatterns = [
    path("webauthn/register/options", views.RegisterOptionsView.as_view(), name="webauthn-register-options"),
    path("webauthn/register/verify", views.RegisterVerifyView.as_view(), name="webauthn-register-verify"),
    path("webauthn/authenticate/options", views.AuthenticateOptionsView.as_view(), name="webauthn-auth-options"),
    path("webauthn/authenticate/verify", views.AuthenticateVerifyView.as_view(), name="webauthn-auth-verify"),
]
