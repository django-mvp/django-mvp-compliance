"""The pages that show a document's wording to a visitor."""

from django.contrib.auth.mixins import LoginRequiredMixin
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
    that version, except on a notice, which nobody agrees to. Used by
    the document's page, which shows any published version. A view using it
    supplies ``get_version()``.
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
        if not user.is_authenticated or version.document.kind == Document.Kind.NOTICE:
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
        context["documents"] = Document.objects.in_force().order_by("name")
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
        return [{"text": self.get_page_title()}]


class AgreedDocumentsView(LoginRequiredMixin, MVPTemplateView):
    """The signed-in person's own list of what they agreed to, in the account area.

    One entry per document people agree to, with the versions this person
    accepted under it, newest first. Takes nothing from the address that could
    name another person, and writes nothing.
    """

    http_method_names = ["get", "head"]
    template_name = "mvp_compliance/agreed_documents.html"
    #: How many of a document's accepted versions are shown before the rest
    #: are folded away. One more than this is shown in full, so that a single
    #: version is never folded on its own.
    shown_first = 3
    page_title = gettext_lazy("Documents you agreed to")
    page_subtitle = gettext_lazy(
        "Each version you accepted on this site, and the date you accepted it. "
        "Open a version to read it exactly as it was."
    )

    def get_breadcrumbs(self):
        return [
            {"text": _("Account Center"), "href": reverse("account-center")},
            {"text": self.page_title},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entries"] = self.get_entries()
        return context

    def get_entries(self) -> list[dict]:
        """Group the person's acceptances into one entry per document.

        Returns:
            One dict per document, in the document's name order, with the
            ``document``, the acceptances ``shown`` and the ``earlier`` ones
            folded away, and ``newer``: the version in force when none of the
            person's acceptances of the document is of it, otherwise ``None``.
            It is read on each request, in one query for the whole page, and
            a person with no acceptances costs no such query.
        """
        acceptances = Acceptance.objects.for_person(
            self.request.user
        ).of_agreed_documents()
        entries: dict[int, dict] = {}
        for acceptance in acceptances:
            document = acceptance.version.document
            entry = entries.setdefault(
                document.pk, {"document": document, "accepted": [], "newer": None}
            )
            entry["accepted"].append(acceptance)
        in_force = {
            version.document_id: version
            for version in Version.objects.current().filter(document__in=list(entries))
        }
        for pk, entry in entries.items():
            accepted = entry.pop("accepted")
            current = in_force.get(pk)
            if current and all(
                acceptance.version_id != current.pk for acceptance in accepted
            ):
                entry["newer"] = current
            fold = len(accepted) > self.shown_first + 1
            entry["shown"] = accepted[: self.shown_first] if fold else accepted
            entry["earlier"] = accepted[self.shown_first :] if fold else []
        return list(entries.values())
