"""Documents and their versions."""

from typing import cast

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from mvp_compliance.exceptions import PublishedVersionError, PublishError
from mvp_compliance.rendering import get_renderer

#: Everything a published version carries except its standing (FR-013) — the
#: one change a published version ever undergoes is draft -> current ->
#: superseded, never a change to what it says.
PUBLISHED_FROZEN_FIELDS = ("document", "number", "markdown", "html", "published_at")


class Document(models.Model):
    """A named legal text with a lasting identity, such as a privacy policy.

    A document holds no wording of its own — every word lives in one of its
    versions.
    """

    name = models.CharField(
        _("name"),
        max_length=100,
        unique=True,
        help_text=_("The name this document is known by, such as “Privacy policy”."),
    )

    class Meta:
        verbose_name = _("document")
        verbose_name_plural = _("documents")

    def __str__(self) -> str:
        return self.name

    @property
    def current(self) -> "Version | None":
        """The version in force, or ``None`` when nothing has been published."""
        return self.versions.current().first()


class VersionQuerySet(models.QuerySet):
    """Enforces that a published version's wording can never change (Article XII).

    ``bulk_update()`` gets no override here: it calls
    ``self.filter(pk__in=pks).update(**update_kwargs)`` internally, so the
    ``update()`` guard below already catches it.
    """

    def update(self, **kwargs) -> int:
        touches_frozen_field = bool(Version.frozen_field_keys() & set(kwargs))
        if touches_frozen_field and self.published().exists():
            raise PublishedVersionError(
                _("A published version's wording cannot be changed.")
            )
        return super().update(**kwargs)

    def delete(self):
        if self.published().exists():
            raise PublishedVersionError(_("A published version cannot be deleted."))
        return super().delete()

    def published(self) -> "VersionQuerySet":
        """Every version that has ever been published, current or superseded."""
        return self.exclude(status=Version.Status.DRAFT)

    def drafts(self) -> "VersionQuerySet":
        return self.filter(status=Version.Status.DRAFT)

    def current(self) -> "VersionQuerySet":
        """The version in force, if any — zero or one row."""
        return self.filter(status=Version.Status.CURRENT)


class VersionManager(models.Manager):
    """Gives a historical model in a migration the same guards (D10).

    Overrides ``get_queryset()`` rather than being built with
    ``Manager.from_queryset()`` — the latter is a dynamic base class mypy
    refuses to type-check (D21, decisions.md). A bare override does not
    forward ``VersionQuerySet``'s own methods onto the manager, so each one
    a related manager needs to expose is forwarded here explicitly.
    """

    use_in_migrations = True

    def get_queryset(self) -> VersionQuerySet:
        return VersionQuerySet(self.model, using=self._db)

    def published(self) -> VersionQuerySet:
        return self.get_queryset().published()

    def drafts(self) -> VersionQuerySet:
        return self.get_queryset().drafts()

    def current(self) -> VersionQuerySet:
        return self.get_queryset().current()


class Version(models.Model):
    """One revision of a document, holding the Markdown its author wrote.

    Numbered and ordered by the package — never given a label or number by
    whoever writes it.
    """

    document = models.ForeignKey(
        Document,
        verbose_name=_("document"),
        help_text=_("The document this version belongs to."),
        related_name="versions",
        on_delete=models.PROTECT,
    )
    number = models.PositiveIntegerField(
        _("number"),
        editable=False,
        help_text=_(
            "This version's position among its document's versions, "
            "assigned automatically."
        ),
    )
    markdown = models.TextField(
        _("markdown"),
        help_text=_("The wording of this version, written in Markdown."),
    )
    html = models.TextField(
        _("html"),
        blank=True,
        help_text=_(
            "The HTML a reader is served, rendered from the markdown once, "
            "at publication. Empty for a draft that has never been published."
        ),
    )

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        CURRENT = "current", _("Current")
        SUPERSEDED = "superseded", _("Superseded")

    status = models.CharField(
        _("status"),
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        editable=False,
        help_text=_(
            "Whether this version is a draft, the version currently in force, "
            "or superseded by a later one."
        ),
    )
    published_at = models.DateTimeField(
        _("published at"),
        null=True,
        blank=True,
        editable=False,
        help_text=_(
            "The moment this version was published. Null for a draft that has "
            "never been published."
        ),
    )

    objects = VersionManager()

    class Meta:
        verbose_name = _("version")
        verbose_name_plural = _("versions")
        ordering = ["document", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "number"],
                name="unique_version_number_per_document",
            ),
            models.UniqueConstraint(
                fields=["document"],
                # Matches Status.CURRENT's value directly — see the note on the
                # check constraint below about a nested Meta's name resolution.
                condition=models.Q(status="current"),
                name="one_current_version_per_document",
            ),
            models.CheckConstraint(
                # A nested Meta class cannot see names bound in Version's own class
                # body, so these match the Status values directly rather than
                # referencing the enum.
                #
                # The published branch names its two standings rather than
                # saying "not draft": status is the one field the queryset
                # guard lets through on a published row, so what it may become
                # is the database's to say.
                condition=models.Q(status="draft", published_at__isnull=True, html="")
                | (
                    models.Q(status__in=["current", "superseded"])
                    & models.Q(published_at__isnull=False)
                    & ~models.Q(html="")
                ),
                name="version_status_agrees_with_its_publication",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document} #{self.number}"

    @property
    def is_published(self) -> bool:
        """Whether this version has ever been published — current or superseded."""
        return self.status != self.Status.DRAFT

    @classmethod
    def frozen_fields(cls) -> list[models.Field]:
        """The fields a published version may never change."""
        return [
            cast(models.Field, cls._meta.get_field(name))
            for name in PUBLISHED_FROZEN_FIELDS
        ]

    @classmethod
    def frozen_field_keys(cls) -> set[str]:
        """Each frozen field's name and attname, so ``document_id`` is caught too."""
        keys: set[str] = set()
        for field in cls.frozen_fields():
            keys.add(field.name)
            keys.add(field.attname)
        return keys

    def publish(self) -> None:
        """Make this draft the version in force, superseding whichever one held it.

        Refuses when this version is not a draft (FR-010), or when the
        rendered output is empty once whitespace is stripped (FR-018, D7) —
        before anything about this row or the document is touched.
        """
        if self.status != self.Status.DRAFT:
            raise PublishError(_("This version has already been published."))

        html = get_renderer()().render(self.markdown)
        if not html.strip():
            raise PublishError(_("Publishing this would produce no output."))

        with transaction.atomic():
            # Not belt-and-braces: MySQL and MariaDB silently omit the partial
            # unique index that otherwise holds "one current version per
            # document" (models.W036), so on those backends this lock is the
            # only thing enforcing FR-007 (research.md R1, D11).
            document = Document.objects.select_for_update().get(pk=self.document_id)
            document.versions.current().update(status=self.Status.SUPERSEDED)
            self.html = html
            self.status = self.Status.CURRENT
            self.published_at = timezone.now()
            self.save(update_fields=["status", "published_at", "html"])

    def save(self, *args, **kwargs) -> None:
        stored = self.stored_row()
        if stored is None:
            current_max = Version.objects.filter(document=self.document).aggregate(
                models.Max("number")
            )["number__max"]
            self.number = (current_max or 0) + 1
        else:
            self.refuse_if_published_wording_changed(stored)
        super().save(*args, **kwargs)

    def stored_row(self) -> dict | None:
        """This row as the database holds it, or ``None`` when it is new.

        Asking the database, rather than asking Django whether this instance
        is being added. An instance built with ``Version(pk=...)`` has never
        been fetched, so Django reports it as being added even though the
        write it is about to make is an update to a row that already exists.
        """
        if self.pk is None:
            return None
        attnames = [field.attname for field in self.frozen_fields()]
        stored = Version.objects.filter(pk=self.pk).values("status", *attnames).first()
        return cast(dict | None, stored)

    def refuse_if_published_wording_changed(self, stored: dict) -> None:
        """Refuse a ``save()`` that changes a frozen field on a published row.

        Compares against the stored row rather than this instance's own
        history, so the check survives ``refresh_from_db``, deferred loading
        and an instance built by a third party.
        """
        if stored["status"] == self.Status.DRAFT:
            return
        attnames = [field.attname for field in self.frozen_fields()]
        if any(stored[attname] != getattr(self, attname) for attname in attnames):
            raise PublishedVersionError(
                _("A published version's wording cannot be changed.")
            )

    def delete(self, *args, **kwargs):
        if self.is_published:
            raise PublishedVersionError(_("A published version cannot be deleted."))
        return super().delete(*args, **kwargs)
