from django.urls import path

from . import views

urlpatterns = [
    path("auth/logout", views.LogoutView.as_view(), name="logout"),
]
