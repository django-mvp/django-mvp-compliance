"""The admin pages for writing, previewing and publishing documents, and for disclosure."""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Prefetch, Q
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from mvp_compliance.exceptions import PublishError
from mvp_compliance.forms import DisclosureForm, TranslationForm, VersionForm
from mvp_compliance.models import (
    Disclosure,
    Document,
    Translation,
    Version,
    declared_documents,
    language_name,
    offered_languages,
)
from mvp_compliance.records import produce, resolve_subject
from mvp_compliance.rendering import get_renderer


class MissingTranslationFilter(admin.SimpleListFilter):
    """Narrow versions to those with no current translation in a language.

    Offered only while the site offers a language, since until then nothing
    about translations appears.
    """

    title = _("Missing a translation")
    parameter_name = "missing_translation"

    def lookups(self, request, model_admin):
        """Offer any offered language, and one choice for a gap in any of them.

        Args:
            request: The current request.
            model_admin: The version admin.

        Returns:
            The choices, empty (hiding the filter) when no language is offered.
        """
        languages = offered_languages()
        if not languages:
            return []
        return [("any", _("Any language")), *languages]

    def queryset(self, request, queryset):
        """Keep the versions lacking a translation in the chosen language.

        Args:
            request: The current request.
            queryset: The versions the list would show.

        Returns:
            The narrowed queryset, or the original when no choice is made.
        """
        choice = self.value()
        if choice == "any":
            return queryset.missing_translation()
        if choice in dict(offered_languages()):
            return queryset.missing_translation(choice)
        return queryset


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """The documents list and each document's page.

    Every column is read from one annotation and one prefetch, so the list
    costs the same number of queries however many documents it shows (#39).
    """

    list_display = [
        "name",
        "kind",
        "enforced",
        "current_version",
        "in_force_since",
        "published_by",
        "published_version_count",
    ]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def get_readonly_fields(self, request, obj=None):
        """Show the slug read-only for a declared document or a published one."""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and (
            obj.slug in declared_documents() or obj.versions.published().exists()
        ):
            readonly.append("slug")
        return readonly

    def get_prepopulated_fields(self, request, obj=None):
        """Drop the prepopulation when the slug is read-only.

        Django indexes the form by every prepopulated field, and a read-only
        field is not on it, so leaving the entry in raises ``KeyError``.
        """
        if "slug" in self.get_readonly_fields(request, obj):
            return {}
        return super().get_prepopulated_fields(request, obj)

    def get_queryset(self, request):
        """Annotate the published count and prefetch the version in force (#39)."""
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            published_version_count=Count(
                "versions",
                filter=Q(
                    versions__status__in=[
                        Version.Status.CURRENT,
                        Version.Status.SUPERSEDED,
                    ]
                ),
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
    editable form, and publishing, locking for translation and returning to
    draft each have a confirmation page behind the ``publish_version``
    permission.
    """

    form = VersionForm
    readonly_fields = [
        "version_number",
        "status",
        "published_at",
        "published_by",
        "html",
        "translation_list",
    ]
    list_display = [
        "document",
        "version_number",
        "status",
        "published_at",
        "published_by",
    ]
    list_select_related = ["document", "publisher"]
    list_filter = ["document", "status", MissingTranslationFilter]
    search_fields = ["document__name"]
    ordering = ["document", F("published_at").desc(nulls_first=True), "-pk"]

    def get_fields(self, request, obj=None):
        """Show the translations only on a pending or published version.

        They are listed when the site offers a language or the version has a
        translation to keep.
        """
        fields = list(super().get_fields(request, obj))
        shown = (
            obj is not None
            and obj.status != Version.Status.DRAFT
            and (offered_languages() or obj.translations.exists())
        )
        if not shown and "translation_list" in fields:
            fields.remove("translation_list")
        return fields

    @admin.display(description=_("Translations"))
    def translation_list(self, version):
        """List each offered language with its translation or a way to add one.

        A translation in a language the site no longer offers, or that has
        become the main language, is kept and listed with a ``data-`` hook
        marking it.

        Args:
            version: The pending or published version the page shows.

        Returns:
            A list with a row per language.
        """
        wordings: dict[str, Translation] = {}
        for translation in version.translations.order_by("published_at", "pk"):
            held = wordings.get(translation.language)
            if (
                held is None
                or translation.status == Translation.Status.CURRENT
                or held.status != Translation.Status.CURRENT
            ):
                wordings[translation.language] = translation
        offered = dict(offered_languages())
        kept = [code for code in wordings if code not in offered]
        rows = [
            self.translation_row(version, code, name, wordings.get(code), False)
            for code, name in offered.items()
        ] + [
            self.translation_row(
                version, code, language_name(code), wordings[code], True
            )
            for code in kept
        ]
        return format_html(
            "<ul data-translations>{}</ul>",
            format_html_join("", "{}", [(row,) for row in rows]),
        )

    def translation_row(self, version, code, name, translation, kept):
        """Build the row for one language.

        Args:
            version: The version the page shows.
            code: The language's code.
            name: The language's name.
            translation: The wording to link, or ``None`` when there is none.
            kept: Whether the language is no longer offered, so a wording in
                it is kept but cannot be added to.

        Returns:
            The row as safe HTML.
        """
        links = []
        if translation is not None:
            links.append(
                format_html(
                    '<a href="{}">{}</a>',
                    reverse(
                        "admin:mvp_compliance_translation_change",
                        args=[translation.pk],
                    ),
                    translation.get_status_display(),
                )
            )
        if not kept and (
            translation is None or translation.status == Translation.Status.CURRENT
        ):
            links.append(
                format_html(
                    '<a href="{}">{}</a>',
                    f"{reverse('admin:mvp_compliance_translation_add')}"
                    f"?version={version.pk}&language={code}",
                    _("Correct") if translation is not None else _("Add"),
                )
            )
        return format_html(
            '<li data-translation-language="{}"{}>{}: {}</li>',
            code,
            mark_safe(" data-translation-kept") if kept else "",
            name,
            format_html_join(" ", "{}", [(link,) for link in links])
            if links
            else _("No translation"),
        )

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

    def get_deleted_objects(self, objs, request):
        """Leave a version's translations out of the permissions a discard needs.

        Discarding a draft or pending version takes its translations with it,
        and that is the version's own permission: a translation put live on it
        cannot be deleted by itself (FR-006).

        Args:
            objs: The versions being deleted.
            request: The current request.

        Returns:
            Django's four values, with translations removed from the
            permissions still missing.
        """
        to_delete, model_count, perms_needed, protected = super().get_deleted_objects(
            objs, request
        )
        perms_needed.discard(Translation._meta.verbose_name)
        return to_delete, model_count, perms_needed, protected

    def has_change_permission(self, request, obj=None):
        """Refuse changing a published or pending version, so Django serves its read-only page."""
        if obj is not None and (
            obj.is_published or obj.status == Version.Status.PENDING
        ):
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
        """Add the preview, publish, lock and return pages."""
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
            path(
                "<int:object_id>/lock/",
                self.admin_site.admin_view(self.lock_view),
                name="mvp_compliance_version_lock",
            ),
            path(
                "<int:object_id>/return-to-draft/",
                self.admin_site.admin_view(self.return_to_draft_view),
                name="mvp_compliance_version_return_to_draft",
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

    def transition_view(self, request, object_id, action, template, title, done):
        """Confirm on GET and apply a change of standing on POST.

        Locking for translation and returning to draft share this shape with
        publishing, and the same permission: each decides what a reader may
        come to be served.

        Args:
            request: The current request.
            object_id: The primary key of the version.
            action: The name of the version method to call, with the caller.
            template: The confirmation template.
            title: The page title.
            done: The message shown when the change was made.

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
                getattr(version, action)(request.user)
            except PublishError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, done)
            return HttpResponseRedirect(
                reverse("admin:mvp_compliance_version_change", args=[version.pk])
            )

        return self.version_page(request, version, template, title)

    def lock_view(self, request, object_id):
        """Confirm on GET and lock the draft for translation on POST.

        Args:
            request: The current request.
            object_id: The primary key of the draft to lock.

        Returns:
            The confirmation page or a redirect to the version's page.
        """
        return self.transition_view(
            request,
            object_id,
            "lock_for_translation",
            "admin/mvp_compliance/version/lock_confirmation.html",
            _("Lock for translation"),
            _("The version is locked for translation."),
        )

    def return_to_draft_view(self, request, object_id):
        """Confirm on GET and return the version to a draft on POST.

        Args:
            request: The current request.
            object_id: The primary key of the pending version to return.

        Returns:
            The confirmation page or a redirect to the version's page.
        """
        return self.transition_view(
            request,
            object_id,
            "return_to_draft",
            "admin/mvp_compliance/version/return_to_draft_confirmation.html",
            _("Return to draft"),
            _("The version is a draft again."),
        )


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    """Writing, previewing and putting live a wording of a version in a language.

    Modelled on :class:`VersionAdmin`. A wording is only added from a pending
    or published version in an offered language, a wording that is not a draft
    has no editable form and cannot be deleted, and putting one live has a
    confirmation page behind ``publish_translation`` alone.
    """

    form = TranslationForm
    readonly_fields = [
        "translating",
        "status",
        "live_since",
        "put_live_by",
        "stored_wording",
    ]
    list_display = [
        "version",
        "language",
        "status",
        "live_since",
        "put_live_by",
    ]
    list_select_related = ["version__document", "publisher"]
    list_filter = ["language", "status"]
    search_fields = ["version__document__name"]

    @admin.display(description=_("Translating"))
    def translating(self, translation):
        """Say which version and language this wording is for.

        Args:
            translation: The wording the page shows.

        Returns:
            The version with the language's name.
        """
        return _("%(version)s into %(language)s") % {
            "version": translation.version,
            "language": translation.language_name,
        }

    @admin.display(description=_("Live since"))
    def live_since(self, translation):
        """Return when a reader could first have been served this wording.

        Args:
            translation: The wording the row or page shows.

        Returns:
            The moment, or ``None`` when no reader has been served it.
        """
        return translation.live_since

    @admin.display(description=_("Put live by"))
    def put_live_by(self, translation):
        """Return who put this wording live.

        Args:
            translation: The wording the row or page shows.

        Returns:
            The wording's ``publisher_display``, ``None`` for a draft.
        """
        return translation.publisher_display

    @admin.display(description=_("Wording a reader is served"))
    def stored_wording(self, translation):
        """Show the HTML stored when this wording was put live.

        Args:
            translation: The wording the page shows.

        Returns:
            The stored HTML, which the renderer sanitised when it was stored.
            Nothing for a draft, which has none.
        """
        return mark_safe(translation.html)  # noqa: S308 - sanitised when stored

    def get_fields(self, request, obj=None):
        """Show the form's fields on a draft and the stored wording on the rest.

        The summary is left out when the version has none to translate.
        """
        if obj is None:
            fields = ["version", "language", "markdown", "summary"]
            version = self.version_from(request.GET.get("version"))
        elif obj.status == Translation.Status.DRAFT:
            fields = ["translating", "markdown", "summary"]
            version = obj.version
        else:
            fields = [
                "translating",
                "status",
                "live_since",
                "put_live_by",
                "markdown",
                "summary",
                "stored_wording",
            ]
            version = obj.version
        if version is not None and not version.summary.strip():
            fields.remove("summary")
        return fields

    def has_change_permission(self, request, obj=None):
        """Refuse changing a wording that is not a draft, so Django serves its read-only page."""
        if obj is not None and obj.status != Translation.Status.DRAFT:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Refuse deleting a wording that is not a draft."""
        if obj is not None and obj.status != Translation.Status.DRAFT:
            return False
        return super().has_delete_permission(request, obj)

    def has_add_permission(self, request):
        """Allow adding only for a pending or published version and an offered language."""
        if not super().has_add_permission(request):
            return False
        return self.version_from(
            request.GET.get("version")
        ) is not None and request.GET.get("language") in dict(offered_languages())

    def version_from(self, version_id):
        """Return the pending or published version a query string names.

        The value comes straight off the query string, so it can be anything.

        Args:
            version_id: The raw ``version`` value from the query string.

        Returns:
            The version, or ``None`` when the value names no version that can
            be translated.
        """
        if not version_id:
            return None
        try:
            return (
                Version.objects.exclude(status=Version.Status.DRAFT)
                .filter(pk=version_id)
                .first()
            )
        except (ValueError, TypeError):
            return None

    def get_changeform_initial_data(self, request):
        """Start a new wording from the wording it will replace."""
        initial = super().get_changeform_initial_data(request)
        current = self.current_wording(request)
        if current is not None:
            initial["markdown"] = current.markdown
            initial["summary"] = current.summary
        return initial

    def current_wording(self, request):
        """Return the wording in force for the version and language the address names.

        Args:
            request: The current request.

        Returns:
            The current translation, or ``None`` when there is none or the
            address names no version.
        """
        version = self.version_from(request.GET.get("version"))
        if version is None:
            return None
        return version.translations.filter(
            language=request.GET.get("language"), status=Translation.Status.CURRENT
        ).first()

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        """Hide Save and add another, and name a correction as one."""
        # Its redirect drops the query string naming the version and language,
        # landing on a form has_add_permission() refuses.
        context["show_save_and_add_another"] = False
        if add and self.current_wording(request) is not None:
            context["title"] = _("Correct a translation")
        return super().render_change_form(
            request, context, add=add, change=change, form_url=form_url, obj=obj
        )

    def get_urls(self):
        """Add the preview and publish pages."""
        urls = [
            path(
                "<int:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="mvp_compliance_translation_preview",
            ),
            path(
                "<int:object_id>/publish/",
                self.admin_site.admin_view(self.publish_view),
                name="mvp_compliance_translation_publish",
            ),
        ]
        return urls + super().get_urls()

    def output_for(self, translation):
        """Return the HTML a reader would be served for this wording.

        A draft is rendered here, as publication will. A wording that has been
        put live is read as it was stored, never rendered again.

        Args:
            translation: The wording to show.

        Returns:
            The stored HTML, or a fresh rendering of a draft.
        """
        if translation.status != Translation.Status.DRAFT:
            return translation.html
        return get_renderer()().render(translation.markdown)

    def translation_page(self, request, translation, template, title):
        """Render one of this admin's own pages for a single wording.

        Args:
            request: The current request.
            translation: The wording the page is about.
            template: The template to render.
            title: The page title.

        Returns:
            The rendered page.
        """
        context = {
            **self.admin_site.each_context(request),
            "title": title,
            "opts": self.opts,
            "original": translation,
            "html": self.output_for(translation),
        }
        return TemplateResponse(request, template, context)

    def preview_view(self, request, object_id):
        """Show the rendering a reader will be served.

        Args:
            request: The current request.
            object_id: The primary key of the wording to preview.

        Returns:
            The preview page.

        Raises:
            Http404: No wording has that primary key.
            PermissionDenied: The caller may not view the wording.
        """
        translation = self.get_object(request, object_id)
        if translation is None:
            raise Http404
        if not self.has_view_permission(request, translation):
            raise PermissionDenied

        return self.translation_page(
            request,
            translation,
            "admin/mvp_compliance/translation/preview.html",
            _("Preview"),
        )

    def publish_view(self, request, object_id):
        """Confirm on GET and put the wording live on POST.

        Checks ``publish_translation`` itself: writing a translation and making
        it what readers are served are different levels of trust. A refused
        publication is reported as an error message.

        Args:
            request: The current request.
            object_id: The primary key of the wording to put live.

        Returns:
            The confirmation page on GET, or a redirect to the wording's page
            on POST.

        Raises:
            Http404: No wording has that primary key.
            PermissionDenied: The caller does not hold ``publish_translation``.
        """
        translation = self.get_object(request, object_id)
        if translation is None:
            raise Http404
        if not request.user.has_perm("mvp_compliance.publish_translation"):
            raise PermissionDenied

        if request.method == "POST":
            try:
                translation.publish(publisher=request.user)
            except PublishError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    _("The %(language)s wording of %(version)s is now live.")
                    % {
                        "language": translation.language_name,
                        "version": translation.version,
                    },
                )
            return HttpResponseRedirect(
                reverse(
                    "admin:mvp_compliance_translation_change", args=[translation.pk]
                )
            )

        return self.translation_page(
            request,
            translation,
            "admin/mvp_compliance/translation/publish_confirmation.html",
            _("Put live"),
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
