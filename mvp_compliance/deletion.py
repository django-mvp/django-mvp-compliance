"""Deleting a person's account and what the project holds about them."""

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from mvp_compliance.exceptions import AccountDeletionError
from mvp_compliance.personal_data import PersonalData, kind_path


def delete_account(user: AbstractBaseUser, kinds: list[PersonalData]) -> None:
    """Erase every kind's records about ``user``, then delete the account.

    All of it happens in one transaction: if any step fails, including the
    commit, nothing is deleted. Acceptances are left to
    ``keep_or_remove_acceptances``, as for any removal of an account.

    Args:
        user: The account to delete.
        kinds: The kinds to erase, in the order to erase them.

    Raises:
        AccountDeletionError: When a kind's ``erase``, the deletion of the
            account or the commit fails. It names the kind, or ``"account"``,
            and carries the original error as its cause.
    """
    current = "account"
    try:
        with transaction.atomic():
            for kind in kinds:
                current = kind_path(kind)
                kind.erase(user)
            current = "account"
            user.delete()
    except Exception as error:
        raise AccountDeletionError(current) from error
