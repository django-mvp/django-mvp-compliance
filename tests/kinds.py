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


class OwnTemplate(Notes):
    """A kind that draws itself in the readable copy."""

    template_name = "tests/notes_copy.html"


class BrokenTemplate(Notes):
    """A kind whose own template raises while it is drawn."""

    template_name = "tests/broken_copy.html"


class Failing(PersonalData):
    """A kind that cannot read its records."""

    heading = "Unreadable"

    def collect(self, user):
        raise RuntimeError("the records cannot be read")


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


class MissingField(PersonalData):
    """A kind that lists a field its model does not have."""

    model = Note
    fields = ["title", "nickname"]

    def get_queryset(self, user):
        return Note.objects.filter(owner=user)


class TwoFiles(Notes):
    """A kind with two file fields, which a record can fill with same-named files."""

    fields = ["title", "attachment", "cover"]


class Undumpable(PersonalData):
    """A kind whose own code hands back a value the data file cannot hold."""

    heading = "Raw"

    def collect(self, user):
        return PersonalDataSection(
            key=self.key,
            heading=self.heading,
            columns=(("raw", "Raw"),),
            rows=((b"\x00\x01",),),
        )


class Agreements(Custom):
    """A kind whose key is the one the package's own section has."""


class NotAKind:
    """A class a project could name by mistake."""


class DeletesNotes(Notes):
    """A kind that says its rows are deleted with the queryset."""

    erasure = PersonalData.DELETE


class WithAccount(Notes):
    """A kind whose rows go with the account itself."""

    erasure = PersonalData.WITH_ACCOUNT


class Erases(Notes):
    """A kind that does its own erasing and records that it did."""

    erased: list = []

    def erase(self, user):
        self.erased.append(user.pk)


class ErasesAgain(Erases):
    """A subclass of a kind that overrides ``erase``, which inherits it."""


class StillSilent(Notes):
    """A subclass of a silent kind, which still says nothing."""


class NeitherConstant(Notes):
    """A kind whose erasure is neither constant."""

    erasure = "wipe"


class Refuses(Notes):
    """A kind whose own erasing fails."""

    def erase(self, user):
        raise RuntimeError("the records cannot be erased")
