from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("core.urls")),
]

handler404 = "core.views.not_found"
handler500 = "core.views.server_error"
