"""Tests for mvp_compliance.deletion."""

import pytest

from mvp_compliance.deletion import delete_account
from mvp_compliance.exceptions import AccountDeletionError
from mvp_compliance.models import Acceptance
from mvp_compliance.personal_data import kind_path
from tests.factories import AcceptanceFactory, NoteFactory, UserFactory
from tests.kinds import DeletesNotes, Erases, Refuses, WithAccount
from tests.models import Note, Pin


@pytest.mark.django_db
class TestDeleteAccount:
    """US-1 scenarios 7, 10, 11 and 12, FR-009, FR-011, FR-013."""

    def test_each_kind_erases_once_in_order_and_then_the_user_goes(self, user):
        order = []

        class First(Erases):
            def erase(self, user):
                order.append(
                    ("first", user.pk, type(user).objects.filter(pk=user.pk).exists())
                )

        class Second(Erases):
            def erase(self, user):
                order.append(
                    ("second", user.pk, type(user).objects.filter(pk=user.pk).exists())
                )

        pk = user.pk

        delete_account(user, [First(), Second()])

        assert order == [("first", pk, True), ("second", pk, True)]
        assert not type(user).objects.filter(pk=pk).exists()

    def test_the_rows_a_kind_deletes_are_gone_and_nobody_elses(self, user):
        NoteFactory(owner=user)
        other = NoteFactory(owner=UserFactory())

        delete_account(user, [DeletesNotes()])

        assert list(Note.objects.all()) == [other]

    def test_rows_that_go_with_the_account_go_and_nobody_elses(self, user):
        NoteFactory(owner=user)
        other = NoteFactory(owner=UserFactory())

        delete_account(user, [WithAccount()])

        assert list(Note.objects.all()) == [other]

    def test_a_kind_that_raises_leaves_everything_in_place(self, user):
        NoteFactory(owner=user)
        NoteFactory(owner=user)
        AcceptanceFactory(user=user)

        with pytest.raises(AccountDeletionError) as raised:
            delete_account(user, [DeletesNotes(), Refuses()])

        assert raised.value.kind == kind_path(Refuses())
        assert isinstance(raised.value.__cause__, RuntimeError)
        assert type(user).objects.filter(pk=user.pk).exists()
        assert Note.objects.filter(owner=user).count() == 2
        assert Acceptance.objects.filter(user=user).count() == 1

    def test_a_row_that_protects_the_user_leaves_everything_in_place(self, user):
        NoteFactory(owner=user)
        Pin.objects.create(owner=user)

        with pytest.raises(AccountDeletionError) as raised:
            delete_account(user, [DeletesNotes()])

        assert raised.value.kind == "account"
        assert type(user).objects.filter(pk=user.pk).exists()
        assert Note.objects.filter(owner=user).count() == 1
        assert Pin.objects.filter(owner=user).count() == 1

    def test_acceptances_survive_without_the_user_by_default(self, user):
        AcceptanceFactory(user=user)
        subject = Acceptance.objects.get().subject

        delete_account(user, [])

        (kept,) = Acceptance.objects.all()
        assert kept.user is None
        assert kept.subject == subject

    def test_acceptances_go_with_the_account_when_the_setting_is_off(
        self, user, settings
    ):
        settings.MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL = False
        AcceptanceFactory(user=user)

        delete_account(user, [])

        assert not Acceptance.objects.exists()

    def test_another_persons_acceptances_are_untouched(self, user):
        other = AcceptanceFactory()
        AcceptanceFactory(user=user)

        delete_account(user, [])

        other.refresh_from_db()
        assert other.user is not None
