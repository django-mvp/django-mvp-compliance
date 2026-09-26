"""The addresses a host project mounts to serve its documents as pages.

Mount them with ``path("legal/", include("mvp_compliance.urls"))`` and link
with ``{% url 'mvp_compliance:document' 'privacy-policy' %}``.
"""

from django.urls import path, register_converter

from mvp_compliance.views import DocumentView, VersionView


class VersionNumberConverter:
    """A version's number: a four-digit year, a dot, and a counter, as in ``2026.1``.

    Nothing else matches, so a fixed word such as ``versions`` can never be
    mistaken for a number.
    """

    regex = r"[0-9]{4}\.[0-9]+"

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value: str) -> str:
        return value


register_converter(VersionNumberConverter, "version_number")

app_name = "mvp_compliance"

urlpatterns = [
    path("<slug:slug>/", DocumentView.as_view(), name="document"),
    path(
        "<slug:slug>/<version_number:number>/",
        VersionView.as_view(),
        name="version",
    ),
]
