from django.urls import path

from . import views

urlpatterns = [
    path("auth/otp/request", views.OtpRequestView.as_view(), name="otp-request"),
    path("auth/otp/resend", views.OtpRequestView.as_view(), name="otp-resend"),
    path("auth/otp/verify", views.OtpVerifyView.as_view(), name="otp-verify"),
]
