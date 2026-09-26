"""The pages that show a document's wording to a visitor."""

from django.http import Http404
from django.urls import reverse
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


class VersionView(MVPDetailView):
    """One published version of a document, at an address that never changes.

    Readable by anyone (FR-005). A version that is no longer in force says it
    was replaced, and when; the one in force says so in the document page's
    own words. A draft has no number, so it has no address (FR-007).
    """

    model = Version
    template_name = "mvp_compliance/version_detail.html"
    directory: list[str] = []

    def get_object(self, queryset=None) -> Version:
        """The published version with this number, of the document with this slug.

        Overrides Django's lookup, which filters on a ``slug`` that a version
        does not have.
        """
        versions = (
            Version.objects.published().with_replaced_at().select_related("document")
        )
        try:
            version: Version = versions.get(
                document__slug=self.kwargs["slug"], number=self.kwargs["number"]
            )
        except Version.DoesNotExist:
            raise Http404(_("No version found")) from None
        return version

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["document"] = self.object.document
        return context

    def get_page_title(self):
        return self.object.document.name

    def get_page_subtitle(self):
        version = self.object
        if version.replaced_at is None:
            return _("Version %(number)s, in force since %(date)s") % {
                "number": version.number,
                "date": date_format(timezone.localdate(version.published_at)),
            }
        return _("Version %(number)s") % {"number": version.number}

    def get_breadcrumbs(self):
        # Until there is an index to link back to, the trail starts at the document.
        document = self.object.document
        return [
            {
                "text": document.name,
                "href": reverse("mvp_compliance:document", args=[document.slug]),
            },
            {"text": _("Version %(number)s") % {"number": self.object.number}},
        ]


class VersionListView(MVPDetailView):
    """Every published version of a document, newest first.

    Readable by anyone (FR-005), and "not found" for the same documents that
    ``DocumentView`` refuses: one with nothing in force has no list (FR-007).
    Each row carries the date the version was replaced, from one annotated
    query however many versions there are.
    """

    model = Document
    template_name = "mvp_compliance/version_list.html"
    directory: list[str] = []

    def get_queryset(self):
        return Document.objects.in_force()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["versions"] = (
            self.object.versions.published()
            .with_replaced_at()
            .order_by("-published_at")
        )
        return context

    def get_page_title(self):
        return _("Versions of %(name)s") % {"name": self.object.name}

    def get_breadcrumbs(self):
        document = self.object
        return [
            {
                "text": document.name,
                "href": reverse("mvp_compliance:document", args=[document.slug]),
            },
            {"text": _("Versions")},
        ]
