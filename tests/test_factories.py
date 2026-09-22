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
    def test_two_builds_do_not_collide_on_username(self):
        first = UserFactory()
        second = UserFactory()

        assert first.pk is not None
        assert second.pk is not None
        assert first.username != second.username

    def test_it_builds_an_ordinary_user_by_default(self):
        user = UserFactory()

        assert not user.is_staff
        assert not user.is_superuser

    def test_the_password_it_sets_can_be_used_to_sign_in(self, client):
        user = UserFactory()

        assert client.login(username=user.username, password="password")
