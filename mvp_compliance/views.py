"""The pages that show a document's wording to a visitor."""

from django.http import Http404
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from mvp.views.detail import MVPDetailView
from mvp.views.extra import MVPTemplateView

from mvp_compliance.models import Acceptance, Document, Version


class VersionSubtitleMixin:
    """The line under a page's name: ``v2026.1 · published <date>``.

    Continues with ``· Agreed on <date>`` when the signed-in visitor accepted
    that version. Used by the document's page and a version's page, which say
    the same thing in the same words (FR-009). A view using it supplies
    ``get_version()``.
    """

    def get_version(self) -> Version:
        """The version the line describes."""
        raise NotImplementedError

    def get_page_subtitle(self):
        version = self.get_version()
        line = _("v%(number)s · published %(date)s") % {
            "number": version.number,
            "date": date_format(timezone.localdate(version.published_at)),
        }
        user = self.request.user
        if not user.is_authenticated:
            return line
        agreed_at = (
            Acceptance.objects.for_person(user)
            .filter(version=version)
            .values_list("accepted_at", flat=True)
            .first()
        )
        if agreed_at is None:
            return line
        return _("%(published)s · Agreed on %(date)s") % {
            "published": line,
            "date": date_format(timezone.localdate(agreed_at)),
        }


class DocumentIndexView(MVPTemplateView):
    """Every document that has a version in force, alphabetically.

    Readable by anyone (FR-005). A document with only drafts, or no versions,
    is not listed (FR-007). The index is the root of every page's trail, so its
    own trail is its title alone.
    """

    template_name = "mvp_compliance/document_index.html"
    page_title = gettext_lazy("Legal documents")

    @staticmethod
    def crumb() -> dict[str, str]:
        """The first crumb of every page's trail, linking to this index."""
        return {"text": _("Legal documents"), "href": reverse("mvp_compliance:index")}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["documents"] = Document.objects.in_force().order_by("name")
        return context

    def get_breadcrumbs(self):
        return [{"text": self.get_page_title()}]


class DocumentView(VersionSubtitleMixin, MVPDetailView):
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

    def get_breadcrumbs(self):
        # mvp's default builds its own trail and never reads ``breadcrumbs``.
        return [DocumentIndexView.crumb(), {"text": self.get_page_title()}]


class VersionView(VersionSubtitleMixin, MVPDetailView):
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

    def get_version(self) -> Version:
        """The version this page is about."""
        version: Version = self.object
        return version

    def get_breadcrumbs(self):
        document = self.object.document
        return [
            DocumentIndexView.crumb(),
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
            DocumentIndexView.crumb(),
            {
                "text": document.name,
                "href": reverse("mvp_compliance:document", args=[document.slug]),
            },
            {"text": _("Versions")},
        ]
