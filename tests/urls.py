from django.urls import include, path

urlpatterns = [
    path("legal/", include("mvp_compliance.urls")),
]
