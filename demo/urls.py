from django.contrib import admin
from django.urls import include, path
from mvp.mounted import mount

from demo.mounted import docs
from demo.views import DemoAgreementView

urlpatterns = [
    # The authoring surface this package ships lives entirely in the admin, so
    # the demo mounts it. The pages a visitor reads are the package's own.
    path("admin/", admin.site.urls),
    # Ahead of the include, so the demo's own agreement page answers.
    path("legal/agree/", DemoAgreementView.as_view()),
    path("legal/", include("mvp_compliance.urls")),
    # allauth's sign-in, drawn in the shell by django-mvp-accounts, so a person
    # who is not staff can sign in and see the pages as someone who has agreed
    # to a version.
    path("accounts/", include("allauth.urls")),
    # django-mvp's account area, where this package's own pages for a signed-in
    # person appear. It puts its pages under account/ itself.
    path("", include("mvp.urls")),
    # The demo's pages are the package's documentation, under docs/. They are
    # the site's main app, so their contents are the sidebar on every page that
    # belongs to no other app. Mounted last: the app answers every address
    # nothing above it claims.
    mount("", docs, main=True),
]
