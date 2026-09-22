"""Documents and their versions."""

from typing import cast

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from mvp_compliance.exceptions import (
    PublishedVersionError,
    PublishError,
    RecordedAcceptanceError,
    RecordError,
)
from mvp_compliance.rendering import get_renderer

#: Everything a published version carries except its standing (FR-013) — the
#: one change a published version ever undergoes is draft -> current ->
#: superseded, never a change to what it says.
PUBLISHED_FROZEN_FIELDS = ("document", "number", "markdown", "html", "published_at")


class DocumentQuerySet(models.QuerySet):
    """Answers what a person has outstanding, without a query per document."""

    def outstanding_for(self, user) -> "DocumentQuerySet":
        """Every document in this queryset whose version in force ``user`` has not accepted.

        One query with a subquery rather than a loop, so the cost does not
        grow with the number of documents (FR-012, FR-018, SC-005;
        research.md R4). A document with no version in force is excluded by
        the first filter rather than counted as outstanding — there is
        nothing in force for anybody to accept.
        """
        subject = Acceptance.subject_of(user)
        accepted = Acceptance.objects.filter(
            subject=subject, version__status=Version.Status.CURRENT
        )
        return self.filter(versions__status=Version.Status.CURRENT).exclude(
            pk__in=accepted.values("version__document_id")
        )


class DocumentManager(models.Manager["Document"]):
    """Forwards ``DocumentQuerySet``'s methods, the same shape as ``VersionManager``."""

    def get_queryset(self) -> DocumentQuerySet:
        return DocumentQuerySet(self.model, using=self._db)

    def outstanding_for(self, user) -> DocumentQuerySet:
        return self.get_queryset().outstanding_for(user)


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

    objects = DocumentManager()

    class Meta:
        verbose_name = _("document")
        verbose_name_plural = _("documents")

    def __str__(self) -> str:
        return self.name

    @property
    def current(self) -> "Version | None":
        """The version in force, or ``None`` when nothing has been published."""
        return self.versions.current().first()

    def is_outstanding_for(self, user) -> bool:
        """Whether ``user`` has not accepted the version currently in force (FR-011).

        The ``outstanding_for`` queryset narrowed to this document's primary
        key, rather than a second expression of the rule (D11). ``False``
        when nothing is in force — a normal answer, not an error.
        """
        return Document.objects.outstanding_for(user).filter(pk=self.pk).exists()


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
        # Writing a version and making one legally binding are different levels
        # of trust, so publishing needs a permission Django does not create on
        # its own (FR-014). A site that wants one person to do both grants both.
        permissions = [("publish_version", _("Can publish a version"))]
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

    @staticmethod
    def same_wording(one: str, other: str) -> bool:
        """Whether two wordings say the same thing.

        Neither difference this ignores is one a reader would see. A
        browser stores a text area's content with a carriage return before
        every newline, so a draft written in one carries them and a
        wording written any other way does not, and a trailing newline is
        present or absent depending on how each was entered.
        """
        return one.replace("\r\n", "\n").strip() == other.replace("\r\n", "\n").strip()

    def publish(self) -> None:
        """Make this draft the version in force, superseding whichever one held it.

        Refuses when this version is not a draft (FR-010), when the
        rendered output is empty once whitespace is stripped (FR-018, D7),
        or when it says exactly what the version in force already says
        (D23) — each before anything about this row or the document is
        touched.
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
            # Under the lock, ask the row rather than this instance. The check
            # above reads a copy of the standing that may be older than the
            # row, which is what a second process publishing first looks like
            # from here (FR-010).
            stored = self.stored_row()
            if stored is None or stored["status"] != self.Status.DRAFT:
                raise PublishError(_("This version is no longer a draft."))
            # Read under the same lock, because this is the one refusal whose
            # answer can change while a draft sits unpublished. A draft that
            # duplicates today's version in force is a different draft once
            # somebody publishes another one, so asking any earlier than here
            # answers a question about a document that has since moved (D23).
            current = document.versions.current().first()
            if current is not None and self.same_wording(
                self.markdown, current.markdown
            ):
                raise PublishError(
                    _("This says exactly what the version in force already says.")
                )
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


def acceptances_survive_account_removal() -> bool:
    """Whether the package's default is to keep a person's acceptances (FR-013).

    Read at the point of use, not cached, so a change to
    ``MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL`` takes effect on the
    next account removal rather than needing a restart (research.md R1).
    """
    return getattr(
        settings, "MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL", True
    )


def keep_or_remove_acceptances(collector, field, sub_objs, using) -> None:
    """The ``on_delete`` callable on ``Acceptance.user`` (D8, research.md R1).

    ``on_delete`` accepts any callable with this signature — it is all
    ``SET_NULL`` and ``CASCADE`` are — so this one reads
    ``acceptances_survive_account_removal()`` at the moment a delete runs and
    delegates to Django's own implementation of whichever the setting names.
    Reading the setting here rather than at import time is what makes it a
    setting rather than a constant baked in when the model class was built,
    and what makes it testable with ``override_settings``.

    ``Acceptance.user`` stays ``null=True`` even though this callable is not
    literally ``SET_NULL``: ``ForeignKey._check_on_delete`` compares
    ``on_delete == SET_NULL`` by identity, so it does not recognise a
    callable that only delegates to ``SET_NULL`` and will not flag a missing
    ``null=True`` the way it would for the real thing.

    This callable must never be given a ``lazy_sub_objs`` attribute the way
    Django's own ``SET_NULL`` is. Its absence is what makes the collector
    evaluate ``sub_objs`` before calling in, which sends the resulting field
    update down the raw ``UpdateQuery`` path rather than
    ``AcceptanceQuerySet.update()`` — where it would hit that queryset's
    refusal and turn every account deletion under the package's default into
    an unhandled error.
    """
    if acceptances_survive_account_removal():
        models.SET_NULL(collector, field, sub_objs, using)
    else:
        models.CASCADE(collector, field, sub_objs, using)


class AcceptanceQuerySet(models.QuerySet):
    """Refuses every route that would change or delete a recorded acceptance (Article XII)."""

    def update(self, **kwargs) -> int:
        if self.exists():
            raise RecordedAcceptanceError(
                _("An acceptance cannot be changed once it is recorded.")
            )
        return super().update(**kwargs)

    def delete(self):
        raise RecordedAcceptanceError(_("An acceptance cannot be deleted."))


class AcceptanceManager(models.Manager["Acceptance"]):
    """Where an acceptance is written — see ``record()``.

    Gives a historical model in a migration the same guards (``use_in_migrations``).
    Overrides ``get_queryset()`` rather than being built with
    ``Manager.from_queryset()`` — the latter is a dynamic base class mypy
    refuses to type-check (specs/001-legal-documents-kept/decisions.md D21).
    """

    use_in_migrations = True

    def get_queryset(self) -> AcceptanceQuerySet:
        return AcceptanceQuerySet(self.model, using=self._db)

    def record(self, user, version, request=None) -> "Acceptance":
        """Record ``user``'s acceptance of ``version``.

        Refuses a version that has never been published (FR-003) before
        anything is written. Recording the same person's acceptance of the
        same version again, including when two attempts race, returns the
        record that already exists rather than raising or writing a second
        one (FR-009, FR-010). ``request`` is accepted for a later story's use
        and is not read here.
        """
        if not version.is_published:
            raise RecordError(
                _(
                    "Cannot record an acceptance of a version that has never been published."
                )
            )
        subject = Acceptance.subject_of(user)
        return self.get_or_create(
            subject=subject,
            version=version,
            defaults={"user": user, "accepted_at": timezone.now()},
        )[0]


class Acceptance(models.Model):
    """The record that one person accepted one published version, at one moment.

    Once written, this record is finished: nothing in this package will ever
    change it or delete it.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        help_text=_(
            "The account that accepted this version, at the time it accepted "
            "it. Null only ever means the account has since been removed — "
            "never that the acceptor was unknown."
        ),
        null=True,
        blank=True,
        on_delete=keep_or_remove_acceptances,
        related_name="compliance_acceptances",
    )
    subject = models.CharField(
        _("subject"),
        max_length=255,
        editable=False,
        help_text=_(
            "The accepted user's primary key, held as text and written once, "
            "when this record is made. The `user` foreign key is cleared when "
            "that account is removed, so without this field the record could "
            "no longer say whose it is or be found among that person's others."
        ),
    )
    version = models.ForeignKey(
        Version,
        verbose_name=_("version"),
        help_text=_(
            "The published version this acceptance names. Never a draft — "
            "recording an acceptance of one is refused."
        ),
        on_delete=models.PROTECT,
        related_name="acceptances",
    )
    accepted_at = models.DateTimeField(
        _("accepted at"),
        editable=False,
        db_index=True,
        help_text=_(
            "The moment this acceptance was recorded. Set once, when the "
            "record is made, and never rewritten."
        ),
    )
    ip_address = models.GenericIPAddressField(
        _("IP address"),
        null=True,
        blank=True,
        help_text=_(
            "The address the request came from when this acceptance was "
            "recorded. Held only when the host project has turned that on and "
            "supplied the request — personal data about someone who did not "
            "ask for it to be kept, so it is the host project's decision."
        ),
    )

    objects = AcceptanceManager()

    class Meta:
        verbose_name = _("acceptance")
        verbose_name_plural = _("acceptances")
        ordering = ["accepted_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "version"],
                # Over `subject` rather than `user`: a later story clears the
                # user foreign key when that account is removed, and a
                # constraint over `user` would stop holding at exactly the
                # moment nobody is watching.
                name="one_acceptance_per_person_per_version",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.subject} accepted {self.version}"

    @staticmethod
    def subject_of(user) -> str:
        """The identifier ``record()`` writes and a later story's lookups read back.

        The single place the identifier is derived, so writing and reading
        cannot disagree about what identifies a person.
        """
        if user.pk is None:
            raise RecordError(
                _("Cannot record an acceptance for a user with no primary key.")
            )
        return str(user.pk)

    def save(self, *args, **kwargs) -> None:
        if self.pk is not None and Acceptance.objects.filter(pk=self.pk).exists():
            raise RecordedAcceptanceError(
                _("An acceptance cannot be changed once it is recorded.")
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RecordedAcceptanceError(_("An acceptance cannot be deleted."))
