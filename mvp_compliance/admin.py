"""The admin pages for writing, previewing and publishing documents, and for disclosure."""

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
    """The documents list and each document's page.

    Every column is read from one annotation and one prefetch, so the list
    costs the same number of queries however many documents it shows (#39).
    """

    list_display = [
        "name",
        "current_version",
        "in_force_since",
        "published_by",
        "published_version_count",
    ]
    search_fields = ["name"]

    def get_queryset(self, request):
        """Annotate the published count and prefetch the version in force (#39)."""
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
        """Return the document's current version from the prefetch in ``get_queryset``.

        Args:
            document: A document fetched through this admin's queryset.

        Returns:
            The version in force, or ``None`` when nothing has been published.
        """
        versions = document.current_versions
        return versions[0] if versions else None

    @admin.display(description=_("Current version"))
    def current_version(self, document):
        """Link to the version in force, or say that there is none.

        Args:
            document: A document fetched through this admin's queryset.

        Returns:
            A link to the version's own page, or a note that no version is in force.
        """
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
        """Return when the version in force was published.

        Args:
            document: A document fetched through this admin's queryset.

        Returns:
            The publication time, or ``None`` when nothing has been published.
        """
        version = self.version_in_force(document)
        return version.published_at if version else None

    @admin.display(description=_("Published by"))
    def published_by(self, document):
        """Return who published the version in force.

        Args:
            document: A document fetched through this admin's queryset.

        Returns:
            The version's ``publisher_display``, or ``None`` when nothing has been
            published.
        """
        version = self.version_in_force(document)
        return version.publisher_display if version else None

    @admin.display(
        description=_("Published versions"), ordering="published_version_count"
    )
    def published_version_count(self, document):
        """Count the current and superseded versions. A draft has no legal standing.

        Args:
            document: A document fetched through this admin's queryset.

        Returns:
            The number of versions of the document ever published.
        """
        return document.published_version_count


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    """Writing, previewing and publishing versions (FS-002).

    A version is only added from a document, a published version has no
    editable form, and publishing has a confirmation page behind the
    ``publish_version`` permission.
    """

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
        """Return the number a version was published under, or "Draft" until it has one.

        Args:
            version: The version the row or page shows.

        Returns:
            The version's number, or the translated word for a draft.
        """
        return version.number or _("Draft")

    @admin.display(description=_("Published by"))
    def published_by(self, version):
        """Return who published this version.

        Args:
            version: The version the row or page shows.

        Returns:
            The version's ``publisher_display``, which is ``None`` for a draft.
        """
        return version.publisher_display

    def has_delete_permission(self, request, obj=None):
        """Refuse deleting a published version, which ``Version.delete()`` would refuse."""
        if obj is not None and obj.is_published:
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        """Refuse changing a published version, so Django serves its read-only page."""
        if obj is not None and obj.is_published:
            return False
        return super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        """Allow adding only when the query string names an existing document (FS-002)."""
        if not super().has_add_permission(request):
            return False
        return self.document_from(request.GET.get("document")) is not None

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        """Hide Save and add another."""
        # Its redirect drops the query string naming the document, landing on a
        # form has_add_permission() refuses (FS-002).
        context["show_save_and_add_another"] = False
        return super().render_change_form(
            request, context, add=add, change=change, form_url=form_url, obj=obj
        )

    def get_changeform_initial_data(self, request):
        """Start a new version from the wording of the version in force."""
        initial = super().get_changeform_initial_data(request)
        document = self.document_from(initial.get("document"))
        if document is not None and document.current is not None:
            initial["markdown"] = document.current.markdown
        return initial

    def document_from(self, document_id):
        """Return the document a query string names.

        The value comes straight off the query string, so it can be anything.
        A lookup by an identifier that is not a number raises rather than
        finding nothing, and that would put a server error in front of
        somebody who mistyped a link.

        Args:
            document_id: The raw ``document`` value from the query string.

        Returns:
            The document, or ``None`` when the value names no document.
        """
        if not document_id:
            return None
        try:
            return Document.objects.filter(pk=document_id).first()
        except (ValueError, TypeError):
            return None

    def get_urls(self):
        """Add the preview and publish pages."""
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
        """Return the HTML a reader would be served for this version.

        A draft has never been rendered, so it is rendered here. A published
        version's stored ``html`` is the evidence of what somebody was shown,
        so it is read rather than produced again: a fresh rendering can differ
        after a library upgrade or a change to the allow list (Article XII).

        Args:
            version: The version to show.

        Returns:
            The stored HTML of a published version, or a fresh rendering of a
            draft.
        """
        if version.is_published:
            return version.html
        return get_renderer()().render(version.markdown)

    def version_page(self, request, version, template, title):
        """Render one of this admin's own pages for a single version.

        Args:
            request: The current request.
            version: The version the page is about.
            template: The template to render.
            title: The page title.

        Returns:
            The rendered page.
        """
        context = {
            **self.admin_site.each_context(request),
            "title": title,
            "opts": self.opts,
            "original": version,
            "html": self.output_for(version),
        }
        return TemplateResponse(request, template, context)

    def preview_view(self, request, object_id):
        """Show the rendering a reader will be served.

        This is not the editor's inline display, which approximates while
        somebody writes and knows nothing about the allow list. What this page
        shows is what publication stores.

        Args:
            request: The current request.
            object_id: The primary key of the version to preview.

        Returns:
            The preview page.

        Raises:
            Http404: No version has that primary key.
            PermissionDenied: The caller may not view the version.
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
        """Confirm on GET and publish on POST.

        Writing a draft and making something legally binding are different
        levels of trust, so this checks ``publish_version`` itself rather than
        relying on the model or the ordinary change permission. A refused
        publication is reported as an error message.

        Args:
            request: The current request.
            object_id: The primary key of the version to publish.

        Returns:
            The confirmation page on GET, or a redirect to the version's page
            on POST.

        Raises:
            Http404: No version has that primary key.
            PermissionDenied: The caller does not hold ``publish_version``.
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

    Gated on ``produce_disclosure`` alone. Holding every other permission this
    package defines, including the proxy's own ``view_disclosure``, grants
    nothing here (docs/adr/0011-producing-what-is-held-is-an-admin-page-behind-its-own-permission.md).
    """

    def has_view_permission(self, request, obj=None):
        """Allow only holders of ``produce_disclosure``."""
        return request.user.has_perm("mvp_compliance.produce_disclosure")

    def has_module_permission(self, request):
        """Show the admin index entry only to holders of ``produce_disclosure``."""
        return self.has_view_permission(request)

    def has_add_permission(self, request):
        """Refuse adding."""
        return False

    def has_change_permission(self, request, obj=None):
        """Refuse changing."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Refuse deleting."""
        return False

    def get_urls(self):
        """Serve the one page and nothing else."""
        # super() is never called: Django's change view loads the row before any
        # permission check, so its addresses would read any acceptance by pk (FS-004).
        return [
            path(
                "",
                self.admin_site.admin_view(self.changelist_view),
                name="mvp_compliance_disclosure_changelist",
            )
        ]

    def changelist_view(self, request, extra_context=None):
        """Produce the answer for the person the form names."""
        # No ChangeList and no queryset over acceptances, and the refusal comes
        # before anything about the person is read, the same for everybody (FS-004).
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
