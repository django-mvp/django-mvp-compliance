"""Documents and their versions."""

from django.db import models
from django.utils.translation import gettext_lazy as _


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

    class Meta:
        verbose_name = _("version")
        verbose_name_plural = _("versions")
        ordering = ["document", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "number"],
                name="unique_version_number_per_document",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document} #{self.number}"

    def save(self, *args, **kwargs) -> None:
        if self._state.adding:
            current_max = Version.objects.filter(document=self.document).aggregate(
                models.Max("number")
            )["number__max"]
            self.number = (current_max or 0) + 1
        super().save(*args, **kwargs)
