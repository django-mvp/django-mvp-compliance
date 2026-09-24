"""Signals a host project can connect to."""

from django.dispatch import Signal

#: Sent once a version is published and the publication has committed.
#: Sender: the ``Version`` class. Arguments: ``version`` (the version now in force),
#: ``publisher`` (the user who published it, or ``None``), ``replaced`` (the version it
#: superseded, or ``None`` for a document's first).
version_published = Signal()
