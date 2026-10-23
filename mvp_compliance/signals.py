"""Signals a host project can connect to."""

from django.dispatch import Signal

#: Sent once a version is published and the publication has committed.
#: Sender: the ``Version`` class. Arguments: ``version`` (the version now in force),
#: ``publisher`` (the user who published it, or ``None``), ``replaced`` (the version it
#: superseded, or ``None`` for a document's first).
version_published = Signal()

#: Sent each time a person's copy of their data is handed over as a download.
#: Sender: the ``PersonalDataView`` class. Arguments: ``user`` (the person the copy is
#: about) and ``kinds`` (the key of each kind of record the copy holds, in order,
#: ending with ``"agreements"``). Not sent when the copy could not be made.
personal_data_copied = Signal()
