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
    """The line under a page's name: ``v2026.1 - <date>``.

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
        line = _("v%(number)s - %(date)s") % {
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
    """The document's one canonical page: the version in force by default, or any
    published version shown with ``?version=<number>``.

    Readable by anyone (FR-005). A slug that names no document, a document with
    nothing published, or a ``?version=`` value that names no published version
    of it, is "not found" for everybody, signed in or not (FR-007, FR-008).
    Nothing here offers a link to edit or delete: the authoring surface is the
    admin.
    """

    model = Document
    template_name = "mvp_compliance/document_detail.html"
    directory: list[str] = []

    def get_queryset(self):
        return Document.objects.in_force()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["version"] = self.get_version()
        context["versions"] = self.object.versions.published().order_by("-published_at")
        return context

    def get_version(self) -> Version:
        """The version shown: named by ``?version=``, or the one in force.

        One query over ``published().with_replaced_at()``, so the query count
        stays the same whether or not the parameter is given (SC-006).
        """
        number = self.request.GET.get("version")
        versions = self.object.versions.published().with_replaced_at()
        version: Version | None
        if number is None:
            version = versions.filter(status=Version.Status.CURRENT).first()
        else:
            version = versions.filter(number=number).first()
        if version is None:
            raise Http404(_("No version found"))
        return version

    def get_page_title(self):
        return self.object.name

    def get_breadcrumbs(self):
        # mvp's default builds its own trail and never reads ``breadcrumbs``.
        return [DocumentIndexView.crumb(), {"text": self.get_page_title()}]
