from django.urls import path

from . import views

urlpatterns = [
    path("auth/lockout-status", views.LockoutStatusView.as_view(), name="lockout-status"),
    path("security/settings", views.SecuritySettingsView.as_view(), name="security-settings"),
    path("security/credentials/<int:pk>", views.CredentialDetailView.as_view(), name="credential-detail"),
]
