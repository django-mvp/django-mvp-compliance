"""The addresses a host project mounts to serve its documents as pages.

Mount them with ``path("legal/", include("mvp_compliance.urls"))`` and link
with ``{% url 'mvp_compliance:document' 'privacy-policy' %}``.
"""

from django.conf import settings
from django.urls import path

from mvp_compliance.views import (
    AgreedDocumentsView,
    AgreementView,
    DocumentView,
    PersonalDataView,
)

app_name = "mvp_compliance"

urlpatterns = [
    # Ahead of the slug route, so these addresses never answer with a document.
    path("agree/", AgreementView.as_view(), name="agree"),
    path("agreed/", AgreedDocumentsView.as_view(), name="agreed"),
]

# Only while the project declares what it holds, an empty list included: a
# project that says nothing about its own data gets no page. Nothing declared is
# imported here, so a path that cannot be is reported by the system check.
if getattr(settings, "MVP_COMPLIANCE_PERSONAL_DATA", None) is not None:
    urlpatterns.append(path("data/", PersonalDataView.as_view(), name="personal-data"))

urlpatterns.append(path("<slug:slug>/", DocumentView.as_view(), name="document"))
