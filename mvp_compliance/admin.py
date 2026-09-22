"""Registers the authoring surface.

FS-001 scoped itself to the model layer and named this feature as where the
admin, forms and views would arrive (decisions.md D11) — this is that
feature.
"""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from mvp_compliance.exceptions import PublishError
from mvp_compliance.forms import VersionForm
from mvp_compliance.models import Document, Version
from mvp_compliance.rendering import get_renderer


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    form = VersionForm
    readonly_fields = ["number", "status", "published_at", "html"]
    list_display = ["document", "number", "status", "published_at"]
    list_filter = ["status"]
    search_fields = ["document__name"]
    ordering = ["document", "-number"]

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
                version.publish()
            except PublishError as exc:
                messages.error(request, str(exc))
            return HttpResponseRedirect(
                reverse("admin:mvp_compliance_version_change", args=[version.pk])
            )

        return self.version_page(
            request,
            version,
            "admin/mvp_compliance/version/publish_confirmation.html",
            _("Publish"),
        )
