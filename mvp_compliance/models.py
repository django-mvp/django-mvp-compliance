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
