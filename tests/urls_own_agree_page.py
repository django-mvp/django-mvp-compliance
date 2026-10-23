"""A project that answers the page that asks with a view of its own, as the demo does."""

from django.http import HttpResponse
from django.urls import include, path


def own_agreement_page(request):
    return HttpResponse("the project's own page")


urlpatterns = [
    # Ahead of the include, so the address resolves outside the package's namespace.
    path("legal/agree/", own_agreement_page),
    path("accounts/", include("allauth.urls")),
    path("legal/", include("mvp_compliance.urls")),
]
