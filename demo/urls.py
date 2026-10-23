from django.contrib import admin
from django.urls import include, path

from demo.views import DemoAgreementView, LandingView

urlpatterns = [
    # The authoring surface this package ships lives entirely in the admin, so
    # the demo mounts it. The pages a visitor reads are the package's own.
    path("admin/", admin.site.urls),
    # Ahead of the include, so the demo's own agreement page answers.
    path("legal/agree/", DemoAgreementView.as_view()),
    path("legal/", include("mvp_compliance.urls")),
    # django-mvp's sign-in and account area, so a person who is not staff can
    # sign in and see the pages as someone who has agreed to a version. It is
    # mounted at the root and puts its pages under account/ itself.
    path("", include("mvp.urls")),
    path("accounts/", include("allauth.urls")),
    path("", LandingView.as_view(), name="landing"),
]
