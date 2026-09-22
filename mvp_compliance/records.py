"""The one answer this package holds about a person.

``produce(subject)`` reads the records held under one subject identifier and
assembles a :class:`PersonalRecord` from them. Nothing here is stored — the
answer is built fresh on every call, and calling it twice with no change to
the records gives an equal answer back (FR-006, D11: no clock is read
anywhere in it).

The package holds one kind of record today — acceptances — so
:func:`produce` returns exactly one :class:`Section`. A further kind of
record joins as another section without :class:`PersonalRecord` changing
shape (FR-017); this module names each kind it knows about rather than
offering a registry for one it does not (FR-018, D1, D9).
"""

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
    the package assigned it.
    """

    document: str
    version: int
    accepted_at: datetime
    ip_address: str | None
    #: The HTML stored on the version at publication (``Version.html``), never
    #: produced again here — the renderer is never called on this path,
    #: because a renderer upgrade or an allow-list change would make the
    #: answer show something nobody was served (Article XIII, FR-010).
    wording: str


@dataclass(frozen=True)
class Section:
    """One kind of record the package holds about a person.

    Carries the partial that renders its entries, so the page can loop over
    sections rather than being written about acceptances specifically
    (FR-017).
    """

    heading: "str | Promise"
    entries: "tuple[AcceptanceEntry, ...]"
    template: str


@dataclass(frozen=True)
class PersonalRecord:
    """The answer: everything the package holds about one subject.

    Its own field names are exactly ``subject`` and ``sections`` — a further
    kind of record can only join as another section (FR-017).
    """

    subject: str
    sections: "tuple[Section, ...]"

    @property
    def is_empty(self) -> bool:
        """Whether no section holds an entry — a normal answer, not an error (FR-005)."""
        return not any(section.entries for section in self.sections)


def resolve_subject(text: str) -> str:
    """The subject identifier ``text`` names, by the order plan.md sets out.

    An account's ``USERNAME_FIELD`` is tried first, then its ``email`` where
    the user model has one, case-insensitively and only when exactly one
    account matches. Neither found, the text is treated as the subject
    itself — the only way to ask about a removed account, whose row is gone
    and whose records carry nothing else to look it up by (research.md R3,
    D10). The ambiguity this accepts — an account whose username is
    literally another account's primary key — is why the produced answer
    reports the subject it was produced for, so a reader can see which
    reading was taken.
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
    """Build the answer for ``subject``, the identifier :class:`Acceptance` records carry.

    One query, whatever the number of documents (SC-008): the acceptances
    are fetched with their version and document in the same query, and
    nothing else is queried.
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
