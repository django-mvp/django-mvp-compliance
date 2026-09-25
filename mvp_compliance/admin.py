"""Registers the authoring surface.

FS-001 scoped itself to the model layer and named this feature as where the
admin, forms and views would arrive (decisions.md D11) — this is that
feature.
"""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Prefetch, Q
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from mvp_compliance.exceptions import PublishError
from mvp_compliance.forms import DisclosureForm, VersionForm
from mvp_compliance.models import Disclosure, Document, Version
from mvp_compliance.records import produce, resolve_subject
from mvp_compliance.rendering import get_renderer


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "current_version",
        "in_force_since",
        "published_by",
        "published_version_count",
    ]
    search_fields = ["name"]

    def get_queryset(self, request):
        """One annotation and one prefetch, so the cost never grows with the row count (#39).

        ``published_version_count`` is a single filtered ``Count`` alongside
        the row's own query; the version in force is fetched once for every
        document on the page rather than once per document, through
        ``prefetch_related``.
        """
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            published_version_count=Count(
                "versions",
                filter=~Q(versions__status=Version.Status.DRAFT),
                distinct=True,
            )
        )
        return queryset.prefetch_related(
            Prefetch(
                "versions",
                queryset=Version.objects.current().select_related("publisher"),
                to_attr="current_versions",
            )
        )

    def version_in_force(self, document):
        """The document's current ``Version``, or ``None`` — read from the prefetch above."""
        versions = document.current_versions
        return versions[0] if versions else None

    @admin.display(description=_("Current version"))
    def current_version(self, document):
        version = self.version_in_force(document)
        if version is None:
            return _("No version in force")
        url = reverse("admin:mvp_compliance_version_change", args=[version.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            _("Version %(number)s") % {"number": version.number},
        )

    @admin.display(description=_("In force since"))
    def in_force_since(self, document):
        version = self.version_in_force(document)
        return version.published_at if version else None

    @admin.display(description=_("Published by"))
    def published_by(self, document):
        version = self.version_in_force(document)
        return version.publisher_display if version else None

    @admin.display(
        description=_("Published versions"), ordering="published_version_count"
    )
    def published_version_count(self, document):
        """Current and superseded versions together — a draft has no legal standing to count."""
        return document.published_version_count


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    form = VersionForm
    readonly_fields = [
        "version_number",
        "status",
        "published_at",
        "published_by",
        "html",
    ]
    list_display = [
        "document",
        "version_number",
        "status",
        "published_at",
        "published_by",
    ]
    list_select_related = ["document", "publisher"]
    list_filter = ["document", "status"]
    search_fields = ["document__name"]
    ordering = ["document", F("published_at").desc(nulls_first=True), "-pk"]

    @admin.display(description=_("number"), ordering="published_at")
    def version_number(self, version):
        """The number a version was published under, or "Draft" until it has one."""
        return version.number or _("Draft")

    @admin.display(description=_("Published by"))
    def published_by(self, version):
        """Who published this version, or the admin's empty value for a draft."""
        return version.publisher_display

    def has_delete_permission(self, request, obj=None):
        """Offer no delete action for a version ``Version.delete()`` would refuse.

        Everything else about view, add, change and delete is left to
        Django's own model permissions.
        """
        if obj is not None and obj.is_published:
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        """A published version offers no editable form at all (D6, FR-017).

        Not disabled fields, not a save Django's own ``save()`` would
        refuse — this is what makes Django serve its own read-only page
        instead of ours.
        """
        if obj is not None and obj.is_published:
            return False
        return super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        """A version can only be added from a document (T065).

        Gates the changelist's add control and the add view itself in one
        place — the query string names the document the same way
        ``get_changeform_initial_data()`` reads it, so a request naming
        none, or one nothing can be resolved from, is refused rather than
        opening a form with nowhere for its wording to belong.
        """
        if not super().has_add_permission(request):
            return False
        return self.document_from(request.GET.get("document")) is not None

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        """No Save and add another (T065).

        Its redirect drops the query string that names the document
        (``response_add()`` sends it to ``request.path``), which would
        land back on a form ``has_add_permission()`` above refuses.
        """
        context["show_save_and_add_another"] = False
        return super().render_change_form(
            request, context, add=add, change=change, form_url=form_url, obj=obj
        )

    def get_changeform_initial_data(self, request):
        """Carry the in-force version's wording when starting the next one.

        The document named in the query string is Django's own default
        initial data (FR-021). With no version in force the box stays
        empty — the ordinary case for a new document (US-5 scenario 3).
        Nothing here opens the in-force version for writing: its markdown
        is read once and handed to a new, unsaved form as a starting
        point (D6, Article XII).
        """
        initial = super().get_changeform_initial_data(request)
        document = self.document_from(initial.get("document"))
        if document is not None and document.current is not None:
            initial["markdown"] = document.current.markdown
        return initial

    def document_from(self, document_id):
        """The document a query string names, or ``None`` when it names none.

        The value arrives straight from the query string, so it can be
        anything at all. Asking the database for a document whose
        identifier is not a number raises rather than returning nothing,
        which would put a server error in front of somebody who mistyped a
        link. Anything the identifier cannot be is treated the same as a
        document that does not exist: the form opens empty.
        """
        if not document_id:
            return None
        try:
            return Document.objects.filter(pk=document_id).first()
        except (ValueError, TypeError):
            return None

    def get_urls(self):
        urls = [
            path(
                "<int:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="mvp_compliance_version_preview",
            ),
            path(
                "<int:object_id>/publish/",
                self.admin_site.admin_view(self.publish_view),
                name="mvp_compliance_version_publish",
            ),
        ]
        return urls + super().get_urls()

    def output_for(self, version):
        """The HTML a reader would be served for this version.

        A draft has never been rendered, so this renders it. A published
        version's stored ``html`` is the evidence of what somebody was
        shown (Article XIII), so this reads that field rather than
        producing it again — a fresh rendering can differ from the stored
        one after a library upgrade or a change to the allow list, and
        showing the fresh one would be showing something nobody was
        served.

        Both pages below answer the same question, so both ask it here.
        """
        if version.is_published:
            return version.html
        return get_renderer()().render(version.markdown)

    def version_page(self, request, version, template, title):
        """Render one of this admin's own pages for a single version."""
        context = {
            **self.admin_site.each_context(request),
            "title": title,
            "opts": self.opts,
            "original": version,
            "html": self.output_for(version),
        }
        return TemplateResponse(request, template, context)

    def preview_view(self, request, object_id):
        """Show the rendering a reader will actually be served (FR-010).

        This is not the editor's own inline display, which approximates
        while somebody writes and knows nothing about the allow list. What
        this page shows is what publication stores.
        """
        version = self.get_object(request, object_id)
        if version is None:
            raise Http404
        if not self.has_view_permission(request, version):
            raise PermissionDenied

        return self.version_page(
            request,
            version,
            "admin/mvp_compliance/version/preview.html",
            _("Preview"),
        )

    def publish_view(self, request, object_id):
        """Confirm on GET, publish on POST — behind its own permission (FR-013, FR-014).

        Writing a draft and making something legally binding are different
        levels of trust, so this checks ``publish_version`` itself rather
        than relying on the model or the ordinary change permission.
        """
        version = self.get_object(request, object_id)
        if version is None:
            raise Http404
        if not request.user.has_perm("mvp_compliance.publish_version"):
            raise PermissionDenied

        if request.method == "POST":
            try:
                version.publish(publisher=request.user)
            except PublishError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    _("Version %(number)s of %(document)s is now published.")
                    % {"number": version.number, "document": version.document},
                )
            return HttpResponseRedirect(
                reverse("admin:mvp_compliance_version_change", args=[version.pk])
            )

        return self.version_page(
            request,
            version,
            "admin/mvp_compliance/version/publish_confirmation.html",
            _("Publish"),
        )


@admin.register(Disclosure)
class DisclosureAdmin(admin.ModelAdmin):
    """The one route that produces everything held about a person.

    Gated on ``produce_disclosure`` alone — holding every other permission
    this package defines, including the proxy's own routine
    ``view_disclosure``, grants nothing here (plan.md Design -> The route,
    decisions.md D2, D7).
    """

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("mvp_compliance.produce_disclosure")

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        """One address, and no way round it — ``super()`` is never called.

        Django's own ``ModelAdmin`` registers add, change, delete and
        history addresses for every model it is given, and its change view
        loads the row before it checks anything. Left in place here they
        would let somebody holding ``produce_disclosure`` read any
        acceptance by guessing its primary key: one at a time, without
        naming a person, and without the statement of coverage an answer
        carries. Refusing them through the permission hooks above is not
        enough, because the row is fetched first.
        """
        return [
            path(
                "",
                self.admin_site.admin_view(self.changelist_view),
                name="mvp_compliance_disclosure_changelist",
            )
        ]

    def changelist_view(self, request, extra_context=None):
        """Replaces the changelist outright — never calls ``super()``.

        No ``ChangeList`` and no queryset over acceptances: registering
        ``Acceptance`` itself, or building one here, would hand everyone
        holding the permission a list of every person's consent history
        (decisions.md D7). The admin's own URL wrapper only checks that the
        caller is active staff, so this raises the real refusal itself,
        before anything about the named person is read — the same refusal
        for a person with records and a person without (FR-013).
        """
        if not self.has_view_permission(request):
            raise PermissionDenied

        form = DisclosureForm(request.GET or None)
        record = None
        if form.is_bound and form.is_valid() and form.cleaned_data["subject"]:
            record = produce(resolve_subject(form.cleaned_data["subject"]))

        context = {
            **self.admin_site.each_context(request),
            "title": _("Everything held about a person"),
            "opts": self.opts,
            "form": form,
            "record": record,
        }
        return TemplateResponse(
            request, "admin/mvp_compliance/disclosure/produce.html", context
        )
