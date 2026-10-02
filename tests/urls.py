from django.urls import include, path

urlpatterns = [
    path("", include("mvp.urls")),
    path("legal/", include("mvp_compliance.urls")),
]
