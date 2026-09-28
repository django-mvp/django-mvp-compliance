"""Exceptions this package raises for invariant breaches.

None subclasses ``ValidationError``, so a breach is never swallowed into a form
field error (docs/adr/0003-refusals-raise-package-exceptions.md).
"""


class PublishedVersionError(Exception):
    """Raised for an attempt to change or delete a published version."""


class PublishError(Exception):
    """Raised when publishing is refused."""


class RecordedAcceptanceError(Exception):
    """Raised for an attempt to change or delete an acceptance."""


class RecordError(Exception):
    """Raised when recording an acceptance is refused."""
