"""Kinds of record the tests declare, by dotted path, in the setting."""

from mvp_compliance.personal_data import PersonalData, PersonalDataSection
from tests.models import Note


class Notes(PersonalData):
    """A model, five fields and a queryset in title order."""

    heading = "Your notes"
    description = "Every note you wrote."
    model = Note
    fields = ["title", "status", "topic", "summary", "attachment"]

    def get_queryset(self, user):
        return Note.objects.filter(owner=user).order_by("title")


class Bare(PersonalData):
    """A kind that never says whose rows are whose."""

    model = Note
    fields = ["title"]


class Custom(PersonalData):
    """A kind whose data is not one queryset."""

    heading = "Greeting"

    def collect(self, user):
        return PersonalDataSection(
            key=self.key,
            heading=self.heading,
            columns=(("greeting", "Greeting"),),
            rows=((f"Hello, {user.get_username()}",),),
        )
