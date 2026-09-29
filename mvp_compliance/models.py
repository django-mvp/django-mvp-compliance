"""Documents and their versions."""

from functools import partial
from typing import cast

from django.conf import settings
from django.core.validators import RegexValidator
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
from mvp_compliance.signals import version_published

#: Everything a published version carries except its standing. The one change a
#: published version ever undergoes is draft -> current -> superseded.
PUBLISHED_FROZEN_FIELDS = (
    "document",
    "number",
    "markdown",
    "html",
    "published_at",
    "publisher",
    "publisher_subject",
)


#: A slug is lowercase letters and digits, joined by single hyphens. Django's
#: own ``SlugField`` validator also accepts capitals and underscores, which no
#: address of the pages matches (FR-015).
lowercase_slug = RegexValidator(
    regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*\Z",
    message=_("Use lowercase letters, digits and single hyphens only."),
    code="invalid",
)


class DocumentQuerySet(models.QuerySet):
    """Answers what a person has outstanding, and keeps a published slug fixed."""

    def update(self, **kwargs) -> int:
        """Refuse a new slug for any document with a published version (FR-017).

        ``bulk_update()`` calls this, so it is covered too.
        """
        if (
            "slug" in kwargs
            and self.filter(
                versions__status__in=[Version.Status.CURRENT, Version.Status.SUPERSEDED]
            ).exists()
        ):
            raise PublishedVersionError(Document.SLUG_FIXED_MESSAGE)
        return super().update(**kwargs)

    def in_force(self) -> "DocumentQuerySet":
        """Every document with a version in force, each carrying it on ``current_versions``.

        A document with only drafts, or none at all, is absent: nothing of it
        is published for a visitor to read (FR-007). The version is prefetched
        so a page reading it costs no further query per document.
        """
        return self.filter(versions__status=Version.Status.CURRENT).prefetch_related(
            models.Prefetch(
                "versions",
                queryset=Version.objects.current(),
                to_attr="current_versions",
            )
        )

    def outstanding_for(self, user) -> "DocumentQuerySet":
        """Narrow to the documents whose version in force ``user`` has not accepted.

        One query with a subquery rather than a loop, so the cost does not
        grow with the number of documents (FS-003). A document with no version
        in force is not outstanding: there is nothing in force to accept. Nor is
        a notice: nobody accepts one, so nothing of it is ever outstanding.

        Args:
            user: The account to ask about.

        Returns:
            The documents with a version in force that ``user`` has not
            accepted, notices left out.
        """
        subject = Acceptance.subject_of(user)
        accepted = Acceptance.objects.filter(
            subject=subject, version__status=Version.Status.CURRENT
        )
        return (
            self.filter(versions__status=Version.Status.CURRENT)
            .exclude(kind=Document.Kind.NOTICE)
            .exclude(pk__in=accepted.values("version__document_id"))
        )


class DocumentManager(models.Manager["Document"]):
    """Forwards ``DocumentQuerySet``'s methods, the same shape as ``VersionManager``."""

    def get_queryset(self) -> DocumentQuerySet:
        """Return a ``DocumentQuerySet``."""
        return DocumentQuerySet(self.model, using=self._db)

    def in_force(self) -> DocumentQuerySet:
        return self.get_queryset().in_force()

    def outstanding_for(self, user) -> DocumentQuerySet:
        """Return the documents whose version in force ``user`` has not accepted.

        Args:
            user: The account to ask about.

        Returns:
            The result of ``DocumentQuerySet.outstanding_for``.
        """
        return self.get_queryset().outstanding_for(user)


class Document(models.Model):
    """A named legal text with a lasting identity, such as a privacy policy.

    A document holds no wording of its own — every word lives in one of its
    versions. Its kind says whether people agree to it or only read it.
    """

    class Kind(models.TextChoices):
        AGREED = "agreed", _("Agreed to")
        NOTICE = "notice", _("Notice")

    name = models.CharField(
        _("name"),
        max_length=100,
        unique=True,
        help_text=_("The name this document is known by, such as “Privacy policy”."),
    )
    slug = models.SlugField(
        _("slug"),
        max_length=100,
        unique=True,
        validators=[lowercase_slug],
        help_text=_(
            "The document's identifier in its address, such as “privacy-policy”."
        ),
    )
    kind = models.CharField(
        _("kind"),
        max_length=10,
        choices=Kind.choices,
        default=Kind.AGREED,
        help_text=_(
            "Whether people agree to this document, such as a privacy policy, or only "
            "read it, such as an impressum. Nobody is ever asked to accept a notice."
        ),
    )

    SLUG_FIXED_MESSAGE = _(
        "A document's slug cannot be changed once a version of it has been published."
    )

    objects = DocumentManager()

    class Meta:
        verbose_name = _("document")
        verbose_name_plural = _("documents")

    def __str__(self) -> str:
        """Return the document's name."""
        return self.name

    def save(self, *args, **kwargs) -> None:
        """Refuse a new slug once a version has been published; the name stays editable.

        A save whose ``update_fields`` leaves the slug out never writes it, so it
        is not checked.
        """
        update_fields = kwargs.get("update_fields")
        writes_slug = update_fields is None or "slug" in update_fields
        if self.pk is not None and writes_slug:
            stored = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("slug", flat=True)
                .first()
            )
            if (
                stored is not None
                and stored != self.slug
                and self.versions.published().exists()
            ):
                raise PublishedVersionError(self.SLUG_FIXED_MESSAGE)
        super().save(*args, **kwargs)

    @property
    def current(self) -> "Version | None":
        """The version in force, or ``None`` when nothing has been published."""
        return self.versions.current().first()

    def is_outstanding_for(self, user) -> bool:
        """Say whether ``user`` has not accepted the version currently in force.

        Asks ``outstanding_for`` about this one document rather than
        expressing the rule a second time.

        Args:
            user: The account to ask about.

        Returns:
            ``True`` when a version is in force and ``user`` has not accepted
            it. ``False`` when nothing is in force, and always for a notice.
        """
        return Document.objects.outstanding_for(user).filter(pk=self.pk).exists()


class VersionQuerySet(models.QuerySet):
    """Enforces that a published version's wording can never change (Article XI).

    ``bulk_update()`` gets no override here: it calls
    ``self.filter(pk__in=pks).update(**update_kwargs)`` internally, so the
    ``update()`` guard below already catches it.
    """

    def update(self, **kwargs) -> int:
        """Refuse an update touching a frozen field while any row is published."""
        touches_frozen_field = bool(Version.frozen_field_keys() & set(kwargs))
        if touches_frozen_field and self.published().exists():
            raise PublishedVersionError(
                _("A published version's wording and publisher cannot be changed.")
            )
        return super().update(**kwargs)

    def delete(self):
        """Refuse deleting while any row is published."""
        if self.published().exists():
            raise PublishedVersionError(_("A published version cannot be deleted."))
        return super().delete()

    def published(self) -> "VersionQuerySet":
        """Narrow to every version ever published, current or superseded.

        Returns:
            The published versions.
        """
        return self.exclude(status=Version.Status.DRAFT)

    def drafts(self) -> "VersionQuerySet":
        """Narrow to the versions never published.

        Returns:
            The drafts.
        """
        return self.filter(status=Version.Status.DRAFT)

    def current(self) -> "VersionQuerySet":
        """Narrow to the version in force.

        Returns:
            Zero or one row per document.
        """
        return self.filter(status=Version.Status.CURRENT)

    def with_replaced_at(self) -> "VersionQuerySet":
        """Annotate ``replaced_at``: when the next published version took over.

        It is the ``published_at`` of the earliest version of the same document
        published after this one, and ``None`` for the version in force. Drafts
        never count. One query however many versions are read.
        """
        later = (
            Version.objects.published()
            .filter(
                document=models.OuterRef("document"),
                published_at__gt=models.OuterRef("published_at"),
            )
            .order_by("published_at")
        )
        return self.annotate(
            replaced_at=models.Subquery(later.values("published_at")[:1])
        )


class VersionManager(models.Manager):
    """Gives a historical model in a migration the same guards.

    See docs/adr/0004-migrations-are-the-one-route-immutability-cannot-close.md.
    ``VersionQuerySet``'s methods are forwarded explicitly rather than through
    ``Manager.from_queryset()``
    (docs/adr/0006-version-manager-forwards-queryset-methods-explicitly.md).
    """

    use_in_migrations = True

    def get_queryset(self) -> VersionQuerySet:
        """Return a ``VersionQuerySet``."""
        return VersionQuerySet(self.model, using=self._db)

    def published(self) -> VersionQuerySet:
        """Return every version ever published.

        Returns:
            The result of ``VersionQuerySet.published``.
        """
        return self.get_queryset().published()

    def drafts(self) -> VersionQuerySet:
        """Return the versions never published.

        Returns:
            The result of ``VersionQuerySet.drafts``.
        """
        return self.get_queryset().drafts()

    def current(self) -> VersionQuerySet:
        """Return the version in force.

        Returns:
            The result of ``VersionQuerySet.current``.
        """
        return self.get_queryset().current()


class Version(models.Model):
    """One revision of a document, holding the Markdown its author wrote.

    Numbered and ordered by the package — never given a label or number by
    whoever writes it. A draft has no number: it gets one when it is
    published, so a document's published history has no gaps.
    """

    document = models.ForeignKey(
        Document,
        verbose_name=_("document"),
        help_text=_("The document this version belongs to."),
        related_name="versions",
        on_delete=models.PROTECT,
    )
    # Null rather than blank for a draft, so the unique constraint below holds
    # for published numbers alone on every backend.
    number = models.CharField(
        _("number"),
        max_length=20,
        null=True,
        blank=True,
        editable=False,
        help_text=_(
            "The year this version was published and its place among the "
            "document's versions published that year, such as 2026.2. "
            "Assigned at publication. Empty for a draft."
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
    # Cleared by account removal through the plain base manager (FS-005). Never set
    # Meta.base_manager_name: it would route that through VersionQuerySet.update()
    # and make removing an account raise.
    publisher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("publisher"),
        help_text=_(
            "The account that published this version. Empty for a draft, for a "
            "version published from code with nobody named, and once that "
            "account is removed."
        ),
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    publisher_subject = models.CharField(
        _("publisher subject"),
        max_length=255,
        blank=True,
        default="",
        editable=False,
        db_index=True,
        help_text=_(
            "The publisher's primary key as text, written once at publication. "
            "It lets the version say an account was since removed after the "
            "link to it is cleared. Empty when nobody was recorded."
        ),
    )

    objects = VersionManager()

    class Meta:
        verbose_name = _("version")
        verbose_name_plural = _("versions")
        ordering = [
            "document",
            models.F("published_at").asc(nulls_last=True),
            "pk",
        ]
        # Writing a version and making one legally binding are different levels
        # of trust, so publishing has a permission of its own (FS-002).
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
                # Status values are literal: a nested Meta cannot see Version.Status.
                # The published branch names both standings because status is the
                # one field the queryset guard lets through on a published row.
                condition=models.Q(
                    status="draft",
                    number__isnull=True,
                    published_at__isnull=True,
                    html="",
                    publisher__isnull=True,
                    publisher_subject="",
                )
                | (
                    models.Q(status__in=["current", "superseded"])
                    & models.Q(number__isnull=False)
                    & models.Q(published_at__isnull=False)
                    & ~models.Q(html="")
                ),
                name="version_status_agrees_with_its_publication",
            ),
        ]

    def __str__(self) -> str:
        """Return the document's name with the number, or "(draft)"."""
        if self.number is None:
            return f"{self.document} ({_('draft')})"
        return f"{self.document} #{self.number}"

    @property
    def is_published(self) -> bool:
        """Whether this version has ever been published — current or superseded."""
        return self.status != self.Status.DRAFT

    @property
    def publisher_display(self) -> "str | None":
        """Say who published this version.

        Never the subject of an account that has been removed: it names
        nobody a reader could look up, so the version says the account is gone.

        Returns:
            The publisher's name, a note that the account was removed, or a
            note that nobody was recorded. ``None`` for a draft.
        """
        if not self.is_published:
            return None
        if self.publisher_id is not None:
            return str(self.publisher)
        if self.publisher_subject:
            return str(_("Account removed"))
        return str(_("Unknown publisher"))

    @classmethod
    def frozen_fields(cls) -> list[models.Field]:
        """Return the fields a published version may never change.

        Returns:
            The fields named in ``PUBLISHED_FROZEN_FIELDS``.
        """
        return [
            cast(models.Field, cls._meta.get_field(name))
            for name in PUBLISHED_FROZEN_FIELDS
        ]

    @classmethod
    def frozen_field_keys(cls) -> set[str]:
        """Return each frozen field's name and attname.

        Returns:
            The names and attnames, so ``document_id`` is caught as well as
            ``document``.
        """
        keys: set[str] = set()
        for field in cls.frozen_fields():
            keys.add(field.name)
            keys.add(field.attname)
        return keys

    @staticmethod
    def same_wording(one: str, other: str) -> bool:
        """Say whether two wordings say the same thing.

        Line endings and surrounding whitespace are ignored. A browser stores
        a text area's content with a carriage return before every newline, and
        a trailing newline depends on how the wording was entered.

        Args:
            one: A wording in Markdown.
            other: Another wording in Markdown.

        Returns:
            ``True`` when a reader would see no difference between them.
        """
        return one.replace("\r\n", "\n").strip() == other.replace("\r\n", "\n").strip()

    def publish(self, publisher=None) -> None:
        """Make this draft the version in force, superseding whichever one held it.

        Every refusal comes before anything about this row or the document is
        touched. Once the publication commits, ``version_published`` is sent,
        and a receiver that raises cannot undo it
        (docs/adr/0016-a-publication-is-announced-after-it-commits-and-no-receiver-can-undo-it.md).

        Args:
            publisher: The account putting it in force, kept on the version and
                frozen with the wording. ``None`` records nobody.

        Raises:
            PublishError: The version is not a draft, its rendered output is
                empty, or it says exactly what the version in force says.
        """
        if self.status != self.Status.DRAFT:
            raise PublishError(_("This version has already been published."))

        html = get_renderer()().render(self.markdown)
        if not html.strip():
            raise PublishError(_("Publishing this would produce no output."))
        # Before anything about this version changes, so an unsaved publisher
        # is refused with the draft left exactly as it was.
        publisher_subject = (
            "" if publisher is None else Acceptance.subject_of(publisher)
        )

        with transaction.atomic():
            # MySQL and MariaDB silently omit the partial unique index (models.W036),
            # so there this lock alone holds one current version per document
            # (docs/adr/0005-one-version-in-force-is-held-by-two-mechanisms.md).
            document = Document.objects.select_for_update().get(pk=self.document_id)
            # Under the lock, ask the row rather than this instance: the check above
            # read a copy that is stale if a second process published first.
            stored = self.stored_row()
            if stored is None or stored["status"] != self.Status.DRAFT:
                raise PublishError(_("This version is no longer a draft."))
            # Under the same lock, because a draft that duplicates today's version in
            # force stops being a duplicate once somebody publishes another one.
            current = document.versions.current().first()
            if current is not None and self.same_wording(
                self.markdown, current.markdown
            ):
                raise PublishError(
                    _("This says exactly what the version in force already says.")
                )
            document.versions.current().update(status=self.Status.SUPERSEDED)
            if current is not None:
                current.status = self.Status.SUPERSEDED
            self.html = html
            self.status = self.Status.CURRENT
            self.published_at = timezone.now()
            # The site's year, not UTC's, and counted under the lock, so two
            # publications cannot take the same place in it.
            year = (
                timezone.localdate(self.published_at)
                if timezone.is_aware(self.published_at)
                else self.published_at.date()
            ).year
            published_this_year = document.versions.filter(
                number__startswith=f"{year}."
            ).count()
            self.number = f"{year}.{published_this_year + 1}"
            self.publisher = publisher
            self.publisher_subject = publisher_subject
            self.save(
                update_fields=[
                    "status",
                    "number",
                    "published_at",
                    "html",
                    "publisher",
                    "publisher_subject",
                ]
            )
            # Last, so nothing above can raise after it is registered, and
            # inside the block, so a rollback discards it. send_robust logs a
            # failing receiver and carries on: the publication stands.
            transaction.on_commit(
                partial(
                    version_published.send_robust,
                    sender=Version,
                    version=self,
                    publisher=publisher,
                    replaced=current,
                )
            )

    def save(self, *args, **kwargs) -> None:
        """Refuse a save that changes a frozen field on a published row."""
        stored = self.stored_row()
        if stored is not None:
            self.refuse_if_published_wording_changed(stored)
        super().save(*args, **kwargs)

    def stored_row(self) -> dict | None:
        """Return this row as the database holds it.

        Asks the database rather than Django's ``_state.adding``. An instance
        built with ``Version(pk=...)`` has never been fetched, so Django
        reports it as being added even though its write updates a stored row.

        Returns:
            The stored status and frozen fields, or ``None`` when no row exists.
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

        Args:
            stored: The row as ``stored_row()`` returned it.

        Raises:
            PublishedVersionError: The row is published and a frozen field differs.
        """
        if stored["status"] == self.Status.DRAFT:
            return
        attnames = [field.attname for field in self.frozen_fields()]
        if any(stored[attname] != getattr(self, attname) for attname in attnames):
            raise PublishedVersionError(
                _("A published version's wording and publisher cannot be changed.")
            )

    def delete(self, *args, **kwargs):
        """Refuse deleting a published version."""
        if self.is_published:
            raise PublishedVersionError(_("A published version cannot be deleted."))
        return super().delete(*args, **kwargs)


def acceptances_survive_account_removal() -> bool:
    """Say whether acceptances survive the removal of the account they name.

    Read at the point of use, not cached, so a change to the setting takes
    effect on the next account removal
    (docs/adr/0008-an-acceptance-outlives-the-account-it-names.md).

    Returns:
        ``MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL``, ``True`` by default.
    """
    return getattr(settings, "MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL", True)


def keep_or_remove_acceptances(collector, field, sub_objs, using) -> None:
    """Keep or remove a removed account's acceptances, as the setting says.

    The ``on_delete`` callable on ``Acceptance.user``. It reads
    ``acceptances_survive_account_removal()`` when a delete runs and delegates
    to ``SET_NULL`` or ``CASCADE``, so the setting is read at delete time
    rather than baked in when the model class was built
    (docs/adr/0008-an-acceptance-outlives-the-account-it-names.md).

    ``Acceptance.user`` stays ``null=True`` even though this callable is not
    literally ``SET_NULL``: ``ForeignKey._check_on_delete`` compares
    ``on_delete == SET_NULL`` by identity, so it does not recognise a
    callable that only delegates to ``SET_NULL`` and will not flag a missing
    ``null=True`` the way it would for the real thing.

    This callable is not given the ``lazy_sub_objs`` attribute Django's own
    ``SET_NULL`` carries. Two things together would route the resulting field
    update into ``AcceptanceQuerySet.update()`` and have account removal
    refused: that attribute, which leaves ``sub_objs`` unevaluated so the
    collector updates through the queryset rather than a raw ``UpdateQuery``,
    and ``Meta.base_manager_name`` naming ``AcceptanceManager``, which is what
    would put the guarded queryset in the collector's path at all. Neither is
    present, and neither alone does anything — the pair is what a later change
    has to avoid recreating.

    Args:
        collector: Django's deletion collector.
        field: The ``Acceptance.user`` field.
        sub_objs: The acceptances naming the account being removed.
        using: The database alias.
    """
    if acceptances_survive_account_removal():
        models.SET_NULL(collector, field, sub_objs, using)
    else:
        models.CASCADE(collector, field, sub_objs, using)


class AcceptanceQuerySet(models.QuerySet):
    """Refuses every route that would change or delete a recorded acceptance (Article XI)."""

    def update(self, **kwargs) -> int:
        """Refuse every update."""
        # Refused outright: a check-then-update guard would write to a record
        # committed between the two statements.
        raise RecordedAcceptanceError(
            _("An acceptance cannot be changed once it is recorded.")
        )

    def delete(self):
        """Refuse every delete."""
        raise RecordedAcceptanceError(_("An acceptance cannot be deleted."))

    def for_subject(self, subject) -> "AcceptanceQuerySet":
        """Narrow to one person's records.

        Args:
            subject: The identifier that survives the person's account being
                removed, as ``Acceptance.subject_of()`` derives it.

        Returns:
            That person's acceptances.
        """
        return self.filter(subject=subject)


class AcceptanceManager(models.Manager["Acceptance"]):
    """Where an acceptance is written — see ``record()``.

    Gives a historical model in a migration the same guards
    (docs/adr/0004-migrations-are-the-one-route-immutability-cannot-close.md),
    and forwards its queryset's methods explicitly for the reason
    docs/adr/0006-version-manager-forwards-queryset-methods-explicitly.md gives.
    """

    use_in_migrations = True

    def get_queryset(self) -> AcceptanceQuerySet:
        """Return an ``AcceptanceQuerySet``."""
        return AcceptanceQuerySet(self.model, using=self._db)

    def for_subject(self, subject) -> AcceptanceQuerySet:
        """Return one person's records.

        Args:
            subject: The identifier ``Acceptance.subject_of()`` derives.

        Returns:
            The result of ``AcceptanceQuerySet.for_subject``.
        """
        return self.get_queryset().for_subject(subject)

    def for_person(self, user) -> AcceptanceQuerySet:
        """Return a person's acceptances, in the order they happened.

        Args:
            user: The account whose acceptances to return.

        Returns:
            The acceptances recorded under the identifier ``record()`` writes.
        """
        return self.for_subject(Acceptance.subject_of(user))

    def record(self, user, version, request=None) -> "Acceptance":
        """Record ``user``'s acceptance of ``version``.

        Recording the same person's acceptance of the same version again,
        including when two attempts race, returns the record that already
        exists. An existing record is returned untouched, so turning the IP
        address setting on or off never changes what an earlier record holds.

        Args:
            user: The account accepting.
            version: The published version accepted.
            request: The current request. Read only when
                ``MVP_COMPLIANCE_RECORD_IP_ADDRESS`` is on, and only for
                ``REMOTE_ADDR`` on a record being created.

        Returns:
            The acceptance, newly created or already recorded.

        Raises:
            RecordError: ``version`` has never been published, or ``user`` has
                not been saved.
        """
        if not version.is_published:
            raise RecordError(
                _(
                    "Cannot record an acceptance of a version that has never been published."
                )
            )
        ip_address = None
        if request is not None and getattr(
            settings, "MVP_COMPLIANCE_RECORD_IP_ADDRESS", False
        ):
            # Never a forwarded header: the client sets it, so the person the
            # evidence is about could fill it in
            # (docs/adr/0010-the-package-reads-remote-addr-and-no-forwarded-header.md).
            ip_address = request.META.get("REMOTE_ADDR")
        subject = Acceptance.subject_of(user)
        return self.get_or_create(
            subject=subject,
            version=version,
            defaults={
                "user": user,
                "accepted_at": timezone.now(),
                "ip_address": ip_address,
            },
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
                # Over `subject` rather than `user`, which is cleared when the
                # account is removed and would stop the constraint holding.
                name="one_acceptance_per_person_per_version",
            ),
        ]

    def __str__(self) -> str:
        """Return who accepted which version."""
        return f"{self.subject} accepted {self.version}"

    @staticmethod
    def subject_of(user) -> str:
        """Return the identifier ``record()`` writes and every lookup reads back.

        The single place the identifier is derived, so writing and reading
        cannot disagree about what identifies a person. A version's publisher
        is identified the same way.

        Args:
            user: A saved account.

        Returns:
            The account's primary key as text.

        Raises:
            RecordError: ``user`` has not been saved.
        """
        if user.pk is None:
            raise RecordError(
                _(
                    "Cannot record an acceptance or a publisher for a user "
                    "with no primary key."
                )
            )
        return str(user.pk)

    def save(self, *args, **kwargs) -> None:
        """Refuse saving an acceptance that is already recorded."""
        if self.pk is not None and Acceptance.objects.filter(pk=self.pk).exists():
            raise RecordedAcceptanceError(
                _("An acceptance cannot be changed once it is recorded.")
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Refuse every delete."""
        raise RecordedAcceptanceError(_("An acceptance cannot be deleted."))


class Disclosure(Acceptance):
    """Names the act of producing everything held about a person.

    Carries no table of its own — a proxy of :class:`Acceptance` with no
    fields added. It exists for three things a ``ModelAdmin`` needs and this
    package has nowhere else to put: an entry in the admin index, an address,
    and a permission of its own
    (docs/adr/0011-producing-what-is-held-is-an-admin-page-behind-its-own-permission.md).
    Registering ``Acceptance`` itself would hand everyone holding
    ``view_acceptance`` a changelist of every person's consent history,
    which is the risk this permission exists to close.
    """

    class Meta:
        proxy = True
        verbose_name = _("disclosure")
        verbose_name_plural = _("everything held about a person")
        permissions = [
            ("produce_disclosure", _("Can produce everything held about a person"))
        ]
