"""The kinds of record the demo declares it holds about a person."""

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from demo.models import Upload
from mvp_compliance.personal_data import PersonalData


class Profile(PersonalData):
    """The person's own account: always one record."""

    heading = _("Your profile")
    description = _("The name, address and date of the account you signed up with.")
    model = get_user_model()
    fields = ["username", "email", "date_joined"]
    single = True

    def get_queryset(self, user):
        return get_user_model().objects.filter(pk=user.pk)


class Uploads(PersonalData):
    """The files the person uploaded, each with the licence they gave it."""

    heading = _("Files you uploaded")
    description = _("Every file you uploaded, with its title and licence.")
    model = Upload
    fields = ["title", "licence", "uploaded", "file"]

    def get_queryset(self, user):
        return Upload.objects.filter(owner=user)
