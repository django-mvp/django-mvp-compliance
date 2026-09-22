"""Tests for tests.factories — the one factory per model, and no others."""

import pytest

from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    UserFactory,
    VersionFactory,
)


@pytest.mark.django_db
class TestDocumentFactory:
    def test_two_builds_do_not_collide_on_name(self):
        first = DocumentFactory()
        second = DocumentFactory()

        assert first.pk is not None
        assert second.pk is not None
        assert first.name != second.name


@pytest.mark.django_db
class TestVersionFactory:
    def test_two_builds_do_not_collide(self):
        first = VersionFactory()
        second = VersionFactory()

        assert first.pk is not None
        assert second.pk is not None


@pytest.mark.django_db
class TestUserFactory:
    def test_two_builds_do_not_collide(self):
        first = UserFactory()
        second = UserFactory()

        assert first.pk is not None
        assert second.pk is not None
        assert first.username != second.username


@pytest.mark.django_db
class TestAcceptanceFactory:
    def test_it_builds_a_valid_saved_acceptance(self):
        acceptance = AcceptanceFactory()

        assert acceptance.pk is not None
        assert acceptance.subject == str(acceptance.user.pk)
