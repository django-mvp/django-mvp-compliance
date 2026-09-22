"""Tests for tests.factories — the one factory per model, and no others."""

import pytest

from tests.factories import DocumentFactory, UserFactory, VersionFactory


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
