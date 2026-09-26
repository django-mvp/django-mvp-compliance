from django.contrib import admin
from django.urls import include, path

from demo.views import LandingView

urlpatterns = [
    # The authoring surface this package ships lives entirely in the admin, so
    # the demo mounts it. The pages a visitor reads are the package's own.
    path("admin/", admin.site.urls),
    path("legal/", include("mvp_compliance.urls")),
    path("", LandingView.as_view(), name="landing"),
]
