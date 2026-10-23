from django.urls import include, path

urlpatterns = [
    path("", include("mvp.urls")),
    path("accounts/", include("allauth.urls")),
    path("legal/", include("mvp_compliance.urls")),
]
