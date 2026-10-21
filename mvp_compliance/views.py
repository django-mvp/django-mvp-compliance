"""The pages a visitor reads, and the page that asks a person to agree."""

import logging
from urllib.parse import unquote, urljoin, urlsplit

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError, transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import resolve_url
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.csrf import csrf_protect
from mvp.views.detail import MVPDetailView
from mvp.views.extra import MVPTemplateView

from mvp_compliance.models import Acceptance, Document, RecordError, Version

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


@method_decorator(csrf_protect, name="dispatch")
class AgreementView(LoginRequiredMixin, MVPTemplateView):
    """The page that asks a signed-in person to agree to what is outstanding.

    Lists every document outstanding for them, each with a link to its version
    in force and a toggle, and takes all the answers in one submission. A
    submission records the versions agreed to, asks again what is outstanding
    and sends the person on to ``next`` only when the stored acceptances leave
    nothing required. A document is required when it is enforced. Opening the
    page records nothing, and the page stops nobody from going elsewhere.
    """

    template_name = "mvp_compliance/agreement.html"
    page_title = gettext_lazy("Documents to agree to")
    #: The name of the parameter that carries the address to go on to.
    redirect_field_name = "next"

    def get_breadcrumbs(self):
        """Show the page's own title as the whole trail."""
        return [{"text": self.page_title}]

    def get_page_subtitle(self):
        """Say what agreeing is for, according to whether anything is required."""
        if any(not entry["optional"] for entry in self.entries):
            return _(
                "You will not be able to use the app without agreeing to all "
                "required documents."
            )
        return _("Agreeing is optional.")

    def is_optional(self, document: Document) -> bool:
        """Say whether the person may go on without agreeing to ``document``.

        A document is optional when it is not enforced. A project's own view
        may override this to make a document that is not enforced required.
        It must not make an enforced one optional on a site that has switched
        the check on: the check asks ``Document.objects.enforced_outstanding_for()``
        and never the view, so the two would send the person round in a loop.

        Args:
            document: An outstanding document.

        Returns:
            Whether agreeing to ``document`` is optional.
        """
        return not document.enforced

    def get_entries(self) -> list[dict]:
        """Read what is outstanding for the signed-in person, required first.

        Returns:
            One dict per outstanding document, in the order the document pages
            list them, holding its ``document``, the ``version`` in force and
            whether agreeing is ``optional``. Two queries whatever the number
            of documents.
        """
        documents = (
            Document.objects.outstanding_for(self.request.user)
            .in_force()
            .order_by("name")
        )
        entries = [
            {
                "document": document,
                "version": document.current_versions[0],
                "optional": self.is_optional(document),
            }
            for document in documents
        ]
        return sorted(entries, key=lambda entry: entry["optional"])

    def get_destination(self) -> str:
        """Return the address to send the person on to.

        Returns:
            The ``next`` value of the submission or the query string when it
            stays on this site and is not this page, otherwise the address
            named by ``MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL``, ``/`` when the
            project sets none.
        """
        destination: str = self.request.POST.get(
            self.redirect_field_name, self.request.GET.get(self.redirect_field_name, "")
        )
        if url_has_allowed_host_and_scheme(
            destination,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ) and not self.is_own_address(destination):
            return destination
        return resolve_url(
            getattr(settings, "MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL", "/")
        )

    def is_own_address(self, destination: str) -> bool:
        """Say whether ``destination``, read from this page, is this page.

        Args:
            destination: An address on this site, as the person's browser
                would follow it from the page.

        Returns:
            Whether it names this page's path, however it is written: with a
            query string, without the trailing slash, percent-encoded, or as
            ``.`` or a bare query string.
        """
        own: str = self.request.path
        path = unquote(urlsplit(urljoin(own, destination)).path)
        # Resolved again once decoded: a browser reads ``%2e`` as a dot segment.
        path = urlsplit(urljoin(own, path)).path
        return path.rstrip("/") == own.rstrip("/")

    def record_agreed(self, versions: list[Version]) -> None:
        """Record the signed-in person's acceptance of ``versions``.

        The one place the page writes, and the one a project's own view
        overrides to change how an agreement is stored.

        Args:
            versions: The versions the person agreed to.
        """
        Acceptance.objects.record_many(
            self.request.user, versions, request=self.request
        )

    def get(self, request, *args, **kwargs):
        """Send a person on when nothing is required, otherwise draw the page.

        Nothing outstanding sends the person on. So does nothing required when
        the request carries ``next``, whatever its value: they were on their way
        somewhere and are not held up over a document they may leave. Without
        ``next``, a person with only optional documents outstanding is shown
        the page and can accept them.
        """
        self.entries = self.get_entries()
        required = any(not entry["optional"] for entry in self.entries)
        if not required and (
            not self.entries or self.redirect_field_name in request.GET
        ):
            return HttpResponseRedirect(self.get_destination())
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Record what was agreed to, then go on or ask again.

        A submitted version is honoured only when it is the version in force of
        a document outstanding for this person. Whether the person is sent on
        is read from the stored acceptances after the write, never from the
        submission. When the write fails, nothing of it is kept, the failure
        is logged and the page is drawn again with the toggles that were on.
        When a version was replaced, or a document published, since the page
        was drawn, the page is drawn again as ``changed`` rather than
        ``missing``.
        """
        submitted = set(request.POST.getlist("agree"))
        listed = set(request.POST.getlist("listed"))
        self.entries = self.get_entries()
        changed = any(str(entry["version"].pk) not in listed for entry in self.entries)
        agreed = [
            entry["version"]
            for entry in self.entries
            if str(entry["version"].pk) in submitted
        ]
        if agreed:
            try:
                with transaction.atomic():
                    self.record_agreed(agreed)
            except (DatabaseError, RecordError):
                logger.exception(
                    "The agreement of user %s was not recorded", request.user.pk
                )
                return self.render_to_response(self.get_context_data(failed=True))
        self.entries = self.get_entries()
        if all(entry["optional"] for entry in self.entries):
            return HttpResponseRedirect(self.get_destination())
        return self.render_to_response(
            self.get_context_data(changed=changed, missing=not changed)
        )

    def get_context_data(self, **kwargs):
        """Add the entries, each with its toggle's attributes, and the destination."""
        context = super().get_context_data(**kwargs)
        kept = set(self.request.POST.getlist("agree")) if context.get("failed") else ()
        for entry in self.entries:
            slug = entry["document"].slug
            entry["field"] = {
                "name": "agree",
                "value": entry["version"].pk,
                "id": f"agree-{slug}",
                # The label reads "I agree" for every document, so the name
                # reaches assistive technology from the row.
                "aria-describedby": f"document-{slug}",
            }
            if not entry["optional"]:
                entry["field"]["data-required"] = True
            if str(entry["version"].pk) in kept:
                entry["field"]["checked"] = True
        context["entries"] = self.entries
        context["required_count"] = sum(not entry["optional"] for entry in self.entries)
        context["destination"] = self.get_destination()
        context["redirect_field_name"] = self.redirect_field_name
        return context


# --- SKETCH (FS-012): the page a person downloads a copy of their data from. ---
# Stub data, no tests. Rebuilt test-first once the sketch is approved.


class PersonalDataView(LoginRequiredMixin, MVPTemplateView):
    """SKETCH: the account-area page that hands a person a copy of their data."""

    template_name = "mvp_compliance/personal_data.html"
    page_title = gettext_lazy("Your data")
    page_subtitle = gettext_lazy(
        "Download a copy of what this site holds about you, as a single file."
    )

    def dispatch(self, request, *args, **kwargs):
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

    @property
    def state(self) -> str:
        return self.request.GET.get("state", "")

    def get_sections(self) -> list[dict]:
        from demo.sketch_copy import sections

        return [*sections(nothing=self.state == "nothing"), self.get_own_section()]

    def get_own_section(self) -> dict:
        from mvp_compliance import records

        answer = records.produce(str(self.request.user.pk))
        entries = [] if self.state == "nothing" else list(answer.sections[0].entries)
        return {
            "slug": "agreements",
            "heading": _("Documents you agreed to"),
            "description": _(
                "Each version of this site's documents you agreed to, when you agreed, "
                "and the wording you were shown."
            ),
            "acceptances": True,
            "records": entries,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sections"] = kwargs.get("sections") or self.get_sections()
        context["confirmed"] = self.state == "confirmed"
        context.setdefault("form", None if context["confirmed"] else self.get_form())
        return context

    def get_form(self, data=None):
        from mvp_compliance.forms import ConfirmIdentityForm

        return ConfirmIdentityForm(self.request.user, data=data)

    def post(self, request, *args, **kwargs):
        if self.state == "failed":
            return self.render_to_response(self.get_context_data(failed=True))
        if self.state != "confirmed":
            form = self.get_form(request.POST)
            if not form.is_valid():
                return self.render_to_response(self.get_context_data(form=form))
        made_at = timezone.now()
        content = build_copy(request, self.get_sections(), made_at)
        response = HttpResponse(content, content_type="application/zip")
        filename = f"copy-of-your-data-{timezone.localdate(made_at):%Y-%m-%d}.zip"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class PersonalDataCopyView(PersonalDataView):
    """SKETCH ONLY: the readable part of a copy, served so it can be looked at."""

    def get(self, request, *args, **kwargs):
        return HttpResponse(render_copy(request, self.get_sections(), timezone.now()))


def display_sections(sections: list[dict]) -> list[dict]:
    """Pair each value with its label and format it as a person reads it."""
    shown = []
    for section in sections:
        if section.get("acceptances"):
            shown.append(section)
            continue
        rows = [
            [(label, display_value(value)) for label, value in zip(section["labels"], record)]
            for record in section["records"]
        ]
        shown.append({**section, "rows": rows})
    return shown


def display_value(value):
    if hasattr(value, "year") and not isinstance(value, str):
        return {"text": date_format(value)}
    if isinstance(value, dict):
        return {"text": value["name"], "path": value["path"]}
    if value in (None, ""):
        return {"text": None}
    return {"text": value}


def render_copy(request, sections, made_at) -> str:
    from django.contrib.staticfiles import finders
    from django.template.loader import render_to_string
    from mvp.config import MVP_CONFIG

    css = "".join(
        open(finders.find(path), encoding="utf-8").read()
        for path in ["css/django-mvp.css"]
    )
    return render_to_string(
        "mvp_compliance/copy/index.html",
        {
            "css": css,
            "theme": MVP_CONFIG["theme"]["default"],
            "site_name": MVP_CONFIG["layout"]["sidebar"].get("title") or request.get_host(),
            "made_at": made_at,
            "person": request.user.get_username(),
            "sections": display_sections(sections),
        },
    )


def build_copy(request, sections, made_at) -> bytes:
    import io
    import json
    import zipfile

    def as_json(section):
        if section.get("acceptances"):
            records = [
                {
                    "document": entry.document,
                    "version": entry.version,
                    "accepted_at": entry.accepted_at.isoformat(),
                    "wording": entry.wording,
                }
                for entry in section["records"]
            ]
        else:
            records = [
                {
                    label: (value["path"] if isinstance(value, dict) else value)
                    for label, value in zip(section["labels"], record)
                }
                for record in section["records"]
            ]
        return {"key": section["slug"], "heading": str(section["heading"]), "records": records}

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html", render_copy(request, sections, made_at))
        data = {
            "made_at": made_at.isoformat(),
            "person": request.user.get_username(),
            "sections": [as_json(section) for section in sections],
        }
        archive.writestr(
            "data.json", json.dumps(data, indent=2, ensure_ascii=False, default=str)
        )
        for section in sections:
            for record in section["records"] if not section.get("acceptances") else []:
                for value in record:
                    if isinstance(value, dict):
                        archive.writestr(value["path"], f"Placeholder for {value['name']}\n")
    return buffer.getvalue()
