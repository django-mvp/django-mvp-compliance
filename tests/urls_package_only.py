"""A project that mounts the package's pages and not django-mvp's."""

from django.urls import include, path

urlpatterns = [path("legal/", include("mvp_compliance.urls"))]
