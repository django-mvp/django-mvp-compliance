"""The pages that show a document's wording to a visitor."""

import logging

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError, transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import resolve_url
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, ngettext
from mvp.views.detail import MVPDetailView
from mvp.views.extra import MVPTemplateView

from mvp_compliance.exceptions import RecordError
from mvp_compliance.models import Acceptance, Document, Version

logger = logging.getLogger(__name__)


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
    name another person, and writes nothing. Not found in a project that mounts
    no account area.
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

    def dispatch(self, request, *args, **kwargs):
        """Answer "not found" when the project mounts no account area.

        Runs before the sign-in check, so an anonymous visitor to such a project
        is told there is no page rather than sent to sign in for one.

        Raises:
            Http404: When ``account-center`` does not reverse.
        """
        try:
            reverse("account-center")
        except NoReverseMatch:
            raise Http404(_("No account area")) from None
        return super().dispatch(request, *args, **kwargs)

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


class AgreementView(LoginRequiredMixin, MVPTemplateView):
    """The page that asks a signed-in person to agree to what is outstanding.

    Shows the version in force of every document outstanding for them, takes
    one answer per document in a single submission, and sends them on to
    ``?next=`` once the stored acceptances leave nothing outstanding. A person
    with nothing outstanding is sent on without being shown the page.

    A prototype: written to make the page real, with no tests.
    """

    template_name = "mvp_compliance/agreement.html"
    page_title = gettext_lazy("Documents to agree to")
    #: The name of the parameter that carries the address to return to.
    redirect_field_name = "next"

    def get_breadcrumbs(self):
        return [{"text": self.page_title}]

    def get_page_subtitle(self):
        entries = self.get_entries()
        if all(entry["optional"] for entry in entries):
            return ngettext(
                "This document is new or has changed since you last agreed. "
                "Agreeing to it is optional, and you can continue without it.",
                "These documents are new or have changed since you last agreed. "
                "Agreeing to them is optional, and you can continue without them.",
                len(entries),
            )
        return ngettext(
            "This document is new or has changed since you last agreed. "
            "Read it, then tick the box beneath it.",
            "These documents are new or have changed since you last agreed. "
            "Read each one, then tick the box beneath it.",
            len(self.get_entries()),
        )

    def get_destination(self) -> str:
        """The address to send the person on to: ``next`` when it stays on this site."""
        destination = self.request.POST.get(
            self.redirect_field_name, self.request.GET.get(self.redirect_field_name, "")
        )
        safe = url_has_allowed_host_and_scheme(
            destination,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        )
        if not safe or destination.split("?")[0] == self.request.path:
            return resolve_url(
                getattr(settings, "MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL", "/")
            )
        return destination

    def get_entries(self) -> list[dict]:
        """One entry per outstanding document, in the order the document pages use.

        Each carries the ``document``, the ``version`` in force, and
        ``previous``: the person's latest acceptance of an earlier version of
        it, or ``None``. Read once per request.
        """
        if not hasattr(self, "entries"):
            user = self.request.user
            documents = (
                Document.objects.outstanding_for(user).in_force().order_by("name")
            )
            previous: dict[int, Acceptance] = {}
            for acceptance in (
                Acceptance.objects.for_person(user)
                .filter(version__document__in=documents)
                .select_related("version")
                .order_by("accepted_at")
            ):
                previous[acceptance.version.document_id] = acceptance
            # Faked: enforcement per document does not exist yet. The demo names
            # the documents a person may leave outstanding in a setting, so the
            # page can be looked at with both kinds on it.
            optional = getattr(settings, "MVP_COMPLIANCE_SKETCH_OPTIONAL_SLUGS", ())
            entries = [
                {
                    "document": document,
                    "version": document.current_versions[0],
                    "previous": previous.get(document.pk),
                    "optional": document.slug in optional,
                }
                for document in documents
            ]
            # The ones that hold a person up first, then the ones that do not.
            self.entries = sorted(entries, key=lambda entry: entry["optional"])
        return self.entries

    def get(self, request, *args, **kwargs):
        if not self.get_entries():
            return HttpResponseRedirect(self.get_destination())
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        ticked = set(request.POST.getlist("agree"))
        shown = set(request.POST.getlist("shown"))
        asked = self.get_entries()
        agreed = [entry for entry in asked if str(entry["version"].pk) in ticked]
        notices: dict = {
            "ticked": ticked,
            # Shown a version that has been replaced since: nothing is
            # recorded for it, and the page says why it is back.
            "replaced": [
                entry["document"]
                for entry in asked
                if str(entry["version"].pk) not in shown
            ]
            if shown
            else [],
        }
        if agreed:
            try:
                with transaction.atomic():
                    for entry in agreed:
                        Acceptance.objects.record(
                            request.user, entry["version"], request=request
                        )
            except (DatabaseError, RecordError):
                logger.exception("An acceptance could not be recorded.")
                notices["failed"] = True
                return self.render_to_response(self.get_context_data(**notices))
        # Asked again of the stored records, never taken from the submission.
        del self.entries
        if all(entry["optional"] for entry in self.get_entries()):
            return HttpResponseRedirect(self.get_destination())
        if not agreed and not notices["replaced"]:
            notices["nothing_ticked"] = True
        notices["recorded"] = [entry["document"] for entry in agreed]
        return self.render_to_response(self.get_context_data(**notices))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticked = kwargs.get("ticked", set())
        entries = self.get_entries()
        for entry in entries:
            entry["field"] = {
                "name": "agree",
                "value": entry["version"].pk,
                "id": f"agree-{entry['document'].slug}",
            }
            if str(entry["version"].pk) in ticked:
                entry["field"]["checked"] = True
        context["entries"] = entries
        context["capped"] = len(entries) > 1
        context["required_count"] = sum(not entry["optional"] for entry in entries)
        context["optional_count"] = sum(entry["optional"] for entry in entries)
        context["destination"] = self.get_destination()
        context["redirect_field_name"] = self.redirect_field_name
        return context
