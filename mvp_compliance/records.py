"""The one answer this package holds about a person (FS-004)."""

from dataclasses import dataclass
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from mvp_compliance.models import Acceptance


@dataclass(frozen=True)
class AcceptanceEntry:
    """One acceptance, as it appears in the answer.

    Names the document by its current name, the document's own lasting
    identity rather than something versioned, and the version by the number
    the package assigned it at publication, such as ``"2026.2"``.
    """

    document: str
    version: str
    accepted_at: datetime
    ip_address: str | None
    #: The HTML stored on the version at publication (``Version.html``), never
    #: produced again here, so the answer shows what was served (Article XII).
    wording: str


@dataclass(frozen=True)
class Section:
    """One kind of record the package holds about a person.

    Carries the partial that renders its entries, so the page can loop over
    sections rather than being written about acceptances specifically.
    """

    heading: "str | Promise"
    entries: "tuple[AcceptanceEntry, ...]"
    template: str


@dataclass(frozen=True)
class PersonalRecord:
    """The answer: everything the package holds about one subject.

    Its own field names are exactly ``subject`` and ``sections``. A further
    kind of record joins as another section
    (docs/adr/0012-the-answer-is-sections-not-a-list-of-acceptances.md).
    """

    subject: str
    sections: "tuple[Section, ...]"

    @property
    def is_empty(self) -> bool:
        """Say whether no section holds an entry, a normal answer rather than an error.

        Returns:
            ``True`` when nothing is held under the subject.
        """
        return not any(section.entries for section in self.sections)

    @property
    def coverage(self) -> "str | Promise":
        """Say what the answer covers, whether or not it holds anything.

        "Nothing here" is not "nothing anywhere": this package does not reach
        for a host project's own data, so it says so rather than implying it has.

        Returns:
            The statement, translated.
        """
        return _(
            "This covers what this package holds about this person. The project may "
            "hold further records about them elsewhere that are not included here."
        )


def resolve_subject(text: str) -> str:
    """Return the subject identifier ``text`` names.

    An account's ``USERNAME_FIELD`` is tried first, then its ``email`` where
    the user model has one, case-insensitively and only when exactly one
    account matches. Neither found, the text is treated as the subject
    itself: the only way to ask about a removed account, whose row is gone.
    The answer reports the subject it was produced for, so a reader can see
    which reading was taken.

    Args:
        text: A login name, an email address, or a subject identifier.

    Returns:
        The subject identifier.
    """
    user_model = get_user_model()
    username_field = user_model.USERNAME_FIELD
    account = user_model._default_manager.filter(**{username_field: text}).first()
    if account is not None:
        return str(account.pk)

    try:
        user_model._meta.get_field("email")
    except FieldDoesNotExist:
        return text

    matches = user_model._default_manager.filter(email__iexact=text)[:2]
    if len(matches) == 1:
        return str(matches[0].pk)

    return text


def produce(subject: str) -> PersonalRecord:
    """Build the answer for one person.

    One query, whatever the number of documents. Nothing is stored and no
    clock is read, so two calls with no change to the records give equal
    answers.

    Args:
        subject: The identifier :class:`Acceptance` records carry.

    Returns:
        Everything this package holds under ``subject``.
    """
    acceptances = Acceptance.objects.for_subject(subject).select_related(
        "version", "version__document"
    )
    entries = tuple(
        AcceptanceEntry(
            document=acceptance.version.document.name,
            version=acceptance.version.number,
            accepted_at=acceptance.accepted_at,
            ip_address=acceptance.ip_address,
            wording=acceptance.version.html,
        )
        for acceptance in acceptances
    )
    acceptances_section = Section(
        heading=_("Acceptances"),
        entries=entries,
        template="admin/mvp_compliance/disclosure/acceptances.html",
    )
    return PersonalRecord(subject=subject, sections=(acceptances_section,))
