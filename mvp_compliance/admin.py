"""Registers the authoring surface.

FS-001 scoped itself to the model layer and named this feature as where the
admin, forms and views would arrive (decisions.md D11) — this is that
feature.
"""

from django.contrib import admin

from mvp_compliance.forms import VersionForm
from mvp_compliance.models import Document, Version


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
