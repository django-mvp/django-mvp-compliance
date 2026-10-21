"""The addresses a host project mounts to serve its documents as pages.

Mount them with ``path("legal/", include("mvp_compliance.urls"))`` and link
with ``{% url 'mvp_compliance:document' 'privacy-policy' %}``.
"""

from django.urls import path

from mvp_compliance.views import (
    AgreedDocumentsView,
    AgreementView,
    DocumentView,
    PersonalDataCopyView,
    PersonalDataView,
)

app_name = "mvp_compliance"

urlpatterns = [
    # Ahead of the slug route, so these addresses never answer with a document.
    path("agree/", AgreementView.as_view(), name="agree"),
    path("agreed/", AgreedDocumentsView.as_view(), name="agreed"),
    path("data/", PersonalDataView.as_view(), name="personal-data"),
    # SKETCH ONLY: the readable part of a copy, in the browser.
    path("data/copy/", PersonalDataCopyView.as_view(), name="personal-data-copy"),
    path("<slug:slug>/", DocumentView.as_view(), name="document"),
]
