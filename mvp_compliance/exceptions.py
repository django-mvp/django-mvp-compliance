"""Exceptions this package raises for invariant breaches.

D9: neither subclasses Django's ``ValidationError`` — that is a message for a
form, and swallowing an invariant breach into a field error would be the
silent discard FR-012 forbids.
"""


class PublishedVersionError(Exception):
    """Raised for an attempt to change or delete a published version (FR-011, FR-014)."""


class PublishError(Exception):
    """Raised when publishing is refused: already published, or nothing to publish (FR-010)."""
