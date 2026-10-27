from django.db import DatabaseError

from mvp_compliance.views import AgreementView


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
