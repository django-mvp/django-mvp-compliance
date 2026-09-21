"""Documents and their versions."""

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from mvp_compliance.exceptions import PublishError


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

    class Meta:
        verbose_name = _("version")
        verbose_name_plural = _("versions")
        ordering = ["document", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "number"],
                name="unique_version_number_per_document",
            ),
            models.CheckConstraint(
                # A nested Meta class cannot see names bound in Version's own class
                # body, so this matches Status.DRAFT's value directly rather than
                # referencing the enum.
                condition=models.Q(status="draft", published_at__isnull=True)
                | (~models.Q(status="draft") & models.Q(published_at__isnull=False)),
                name="version_status_agrees_with_published_at",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document} #{self.number}"

    @property
    def is_published(self) -> bool:
        """Whether this version has ever been published — current or superseded."""
        return self.status != self.Status.DRAFT

    def publish(self) -> None:
        """Make this draft the version in force, superseding whichever one held it.

        Refuses when this version is not a draft (FR-010).
        """
        if self.status != self.Status.DRAFT:
            raise PublishError(_("This version has already been published."))

        with transaction.atomic():
            # Not belt-and-braces: MySQL and MariaDB silently omit the partial
            # unique index that otherwise holds "one current version per
            # document" (models.W036), so on those backends this lock is the
            # only thing enforcing FR-007 (research.md R1, D11).
            document = Document.objects.select_for_update().get(pk=self.document_id)
            Version.objects.filter(
                document=document, status=self.Status.CURRENT
            ).update(status=self.Status.SUPERSEDED)
            self.status = self.Status.CURRENT
            self.published_at = timezone.now()
            self.save(update_fields=["status", "published_at"])

    def save(self, *args, **kwargs) -> None:
        if self._state.adding:
            current_max = Version.objects.filter(document=self.document).aggregate(
                models.Max("number")
            )["number__max"]
            self.number = (current_max or 0) + 1
        super().save(*args, **kwargs)
