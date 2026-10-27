"""The addresses a host project mounts to serve its documents as pages.

Mount them with ``path("legal/", include("mvp_compliance.urls"))`` and link
with ``{% url 'mvp_compliance:document' 'privacy-policy' %}``.
"""

from django.conf import settings
from django.urls import path

from mvp_compliance.personal_data import deletion_offered
from mvp_compliance.views import (
    AccountDeletedView,
    AgreedDocumentsView,
    AgreementView,
    ComparisonView,
    DeleteAccountView,
    DocumentView,
    PersonalDataView,
)

app_name = "mvp_compliance"

urlpatterns = [
    # Ahead of the slug route, so these addresses never answer with a document.
    path("agree/", AgreementView.as_view(), name="agree"),
    path("agreed/", AgreedDocumentsView.as_view(), name="agreed"),
    path("deleted/", AccountDeletedView.as_view(), name="account-deleted"),
]

# Only while the project declares what it holds, an empty list included: a
# project that says nothing about its own data gets no page. Nothing declared is
# imported here, so a path that cannot be is reported by the system check.
if getattr(settings, "MVP_COMPLIANCE_PERSONAL_DATA", None) is not None:
    urlpatterns.append(path("data/", PersonalDataView.as_view(), name="personal-data"))

# Only while every declared kind says how it is deleted: a project that has not
# said gets no deletion page and no menu entry.
if deletion_offered():
    urlpatterns.append(
        path("delete/", DeleteAccountView.as_view(), name="delete-account")
    )

urlpatterns.append(
    path("<slug:slug>/compare/", ComparisonView.as_view(), name="comparison")
)
urlpatterns.append(path("<slug:slug>/", DocumentView.as_view(), name="document"))
