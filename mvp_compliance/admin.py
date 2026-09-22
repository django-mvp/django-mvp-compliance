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
