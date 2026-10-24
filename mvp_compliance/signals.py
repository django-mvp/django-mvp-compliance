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

#: Sent once a person has deleted their own account and the deletion has committed.
#: Sender: the ``DeleteAccountView`` class. Arguments: ``user`` (the deleted account,
#: its ``pk`` now ``None`` and its other fields as they were), ``subject`` (its
#: primary key as text, the value its surviving acceptances carry) and ``kinds`` (the
#: key of each declared kind that was deleted, in order). Not sent when the deletion
#: could not be done.
account_deleted = Signal()
