"""The pages that show a document's wording to a visitor."""

from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from mvp.views.detail import MVPDetailView

from mvp_compliance.models import Document, Version


class DocumentView(MVPDetailView):
    """The version of a document in force, at an address that never changes.

    Readable by anyone (FR-005). A slug that names no document, or a document
    with nothing published, is "not found" for everybody, signed in or not
    (FR-007). Nothing here offers a link to edit or delete: the authoring
    surface is the admin.
    """

    model = Document
    template_name = "mvp_compliance/document_detail.html"
    directory: list[str] = []

    def get_queryset(self):
        return Document.objects.in_force()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["version"] = self.get_version()
        return context

    def get_version(self) -> Version:
        """The version in force, already fetched with the document."""
        version: Version = self.object.current_versions[0]
        return version

    def get_page_title(self):
        return self.object.name

    def get_page_subtitle(self):
        version = self.get_version()
        return _("Version %(number)s, in force since %(date)s") % {
            "number": version.number,
            "date": date_format(timezone.localdate(version.published_at)),
        }

    def get_breadcrumbs(self):
        # mvp's default builds its own trail and never reads ``breadcrumbs``.
        # Until there is a page to link back to, the trail is the title alone.
        return [{"text": self.get_page_title()}]
