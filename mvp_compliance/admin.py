"""Registers the authoring surface.

FS-001 scoped itself to the model layer and named this feature as where the
admin, forms and views would arrive (decisions.md D11) — this is that
feature.
"""

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _

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

    def preview_view(self, request, object_id):
        """Show the rendering a reader will actually be served.

        A draft has never been rendered, so this calls ``get_renderer()``
        for it. A published version's stored ``html`` is the evidence of
        what somebody was shown (Article XIII), so this reads that field
        rather than rendering the version again.
        """
        version = self.get_object(request, object_id)
        if version is None:
            raise Http404
        if not self.has_view_permission(request, version):
            raise PermissionDenied

        if version.is_published:
            html = version.html
        else:
            html = get_renderer()().render(version.markdown)

        context = {
            **self.admin_site.each_context(request),
            "title": _("Preview"),
            "opts": self.opts,
            "original": version,
            "html": html,
        }
        return TemplateResponse(
            request, "admin/mvp_compliance/version/preview.html", context
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
            return HttpResponse()

        html = get_renderer()().render(version.markdown)
        context = {
            **self.admin_site.each_context(request),
            "title": _("Publish"),
            "opts": self.opts,
            "original": version,
            "html": html,
        }
        return TemplateResponse(
            request, "admin/mvp_compliance/version/publish_confirmation.html", context
        )
