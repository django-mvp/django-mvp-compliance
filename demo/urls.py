from django.contrib import admin
from django.urls import path

from demo.views import LandingView

urlpatterns = [
    # The authoring surface this package ships lives entirely in the admin, so
    # the demo mounts it. The package registers no addresses of its own.
    path("admin/", admin.site.urls),
    path("", LandingView.as_view(), name="landing"),
]
