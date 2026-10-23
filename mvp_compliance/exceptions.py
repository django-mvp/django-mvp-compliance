"""Exceptions this package raises for invariant breaches.

None subclasses ``ValidationError``, so a breach is never swallowed into a form
field error (docs/adr/0003-refusals-raise-package-exceptions.md).
"""


class AccountDeletionError(Exception):
    """Raised when an account cannot be deleted, and nothing was.

    Attributes:
        kind: The dotted path of the kind whose erasing failed, or
            ``"account"`` when the account itself could not be removed.
    """

    def __init__(self, kind: str) -> None:
        super().__init__(f"The account could not be deleted: {kind} failed.")
        self.kind = kind


class DeclaredDocumentError(Exception):
    """Raised for an attempt to change the slug of a declared document."""


class PersonalDataError(Exception):
    """Raised when one kind of record cannot be put into a person's copy.

    Attributes:
        kind: The dotted path of the kind that failed.
    """

    def __init__(self, kind: str) -> None:
        super().__init__(f"{kind} could not be put into the copy.")
        self.kind = kind


class PublishedVersionError(Exception):
    """Raised for an attempt to change or delete a published version."""


class PublishError(Exception):
    """Raised when publishing is refused."""


class RecordedAcceptanceError(Exception):
    """Raised for an attempt to change or delete an acceptance."""


class RecordError(Exception):
    """Raised when recording an acceptance is refused."""
