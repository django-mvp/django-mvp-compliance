"""Demo only: an account whose acceptances can never be stored.

The page that asks a person to agree has a state for a record that could not be
written, and nothing in an ordinary demo reaches it. Signing in as
``unrecorded.user@example.com`` does.
"""

from django.db import DatabaseError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from mvp_compliance.models import Acceptance

UNRECORDED = "unrecorded.user@example.com"


@receiver(pre_save, sender=Acceptance)
def refuse_the_unrecorded_account(sender, instance, **kwargs):
    if instance.user is not None and instance.user.email == UNRECORDED:
        raise DatabaseError("Demo: this account's acceptances are never stored.")
