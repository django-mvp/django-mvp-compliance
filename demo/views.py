from django.db import DatabaseError
from mvp.views import MVPTemplateView

from mvp_compliance.views import AgreementView


class OverviewView(MVPTemplateView):
    """What the demo shows, and where each part of it is."""

    template_name = "demo/overview.html"
    page_title = "Overview"
    page_subtitle = (
        "Legal documents, a record of who agreed to them, and the pages that ask"
    )


class DocumentsView(MVPTemplateView):
    """The documents the demo is seeded with, and where they are read and written."""

    template_name = "demo/documents.html"
    page_title = "Documents"
    page_subtitle = "Where a document is written, published and read"


class AgreeingView(MVPTemplateView):
    """The pages a signed-in person agrees on, and who to sign in as for each state."""

    template_name = "demo/agreeing.html"
    page_title = "Agreeing"
    page_subtitle = "Being asked to agree, and the list of what a person has agreed to"


class SignInAccountsView(MVPTemplateView):
    """The accounts the demo is seeded with, and what each one can do."""

    template_name = "demo/sign_in_accounts.html"
    page_title = "Sign-in accounts"
    page_subtitle = "Who to sign in as, and what each account can do"


class DemoAgreementView(AgreementView):
    """The agreement page, with a write that fails for one user.

    Signed in as ``unrecorded.user@example.com``, submitting the page shows what a
    person sees when their agreement could not be stored.
    """

    def record_agreed(self, versions):
        """Fail for the demo user whose agreement is never recorded."""
        if self.request.user.email == "unrecorded.user@example.com":
            raise DatabaseError("The demo cannot store this person's agreement.")
        super().record_agreed(versions)
