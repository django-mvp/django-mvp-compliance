"""What the demo holds about a person beyond their account: files they uploaded."""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Upload(models.Model):
    """A file a person uploaded, with its title and the licence they gave it."""

    class Licence(models.TextChoices):
        PRIVATE = "private", _("Private")
        CC_BY = "cc-by", _("Creative Commons Attribution")
        CC0 = "cc0", _("Public domain")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Owner"),
        on_delete=models.CASCADE,
    )
    title = models.CharField(_("Title"), max_length=120)
    licence = models.CharField(
        _("Licence"), max_length=20, choices=Licence, default=Licence.PRIVATE
    )
    uploaded = models.DateTimeField(_("Uploaded"), default=timezone.now)
    file = models.FileField(_("File"), upload_to="uploads/", blank=True)

    class Meta:
        ordering = ["uploaded", "pk"]

    def __str__(self):
        return self.title
