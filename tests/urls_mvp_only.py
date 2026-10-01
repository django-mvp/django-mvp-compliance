"""A project that mounts django-mvp's pages and not the package's."""

from django.urls import include, path

urlpatterns = [path("", include("mvp.urls"))]
