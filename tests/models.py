"""Models the personal-data tests declare kinds over."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Topic(models.Model):
    """Something a note is about: a relation for a kind to read."""

    name = models.CharField(_("Name"), max_length=80)

    def __str__(self):
        return self.name


class Note(models.Model):
    """A person's note, with a choice, a relation, text and a file."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SHARED = "shared", "Shared"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(_("Title"), max_length=80)
    status = models.CharField(
        _("Status"), max_length=10, choices=Status, default=Status.DRAFT
    )
    topic = models.ForeignKey(
        Topic,
        verbose_name=_("Topic"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    summary = models.TextField(_("Summary"), blank=True)
    attachment = models.FileField(_("Attachment"), upload_to="notes/", blank=True)
    cover = models.FileField(_("Cover"), upload_to="covers/", blank=True)
