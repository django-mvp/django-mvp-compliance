from django.conf import settings
from django.db import DatabaseError
from django.views.generic import TemplateView

from mvp_compliance.models import Document
from mvp_compliance.views import AgreementView


class LandingView(TemplateView):
    """The page the components are built for, as far as it exists yet."""

    template_name = "demo/landing.html"


class DemoAgreementView(AgreementView):
    """The agreement page, with optional documents and a write that fails for one user.

    The documents named in ``DEMO_OPTIONAL_DOCUMENT_SLUGS`` are optional, so the page
    shows required and optional rows together. Signed in as
    ``unrecorded.user@example.com``, submitting the page shows what a person sees
    when their agreement could not be stored.
    """

    def is_optional(self, document: Document) -> bool:
        """Answer from the demo's list of optional document slugs.

        Args:
            document: An outstanding document.

        Returns:
            Whether the document's slug is in ``DEMO_OPTIONAL_DOCUMENT_SLUGS``.
        """
        return document.slug in settings.DEMO_OPTIONAL_DOCUMENT_SLUGS

    def record_agreed(self, versions):
        """Fail for the demo user whose agreement is never recorded."""
        if self.request.user.email == "unrecorded.user@example.com":
            raise DatabaseError("The demo cannot store this person's agreement.")
        super().record_agreed(versions)
