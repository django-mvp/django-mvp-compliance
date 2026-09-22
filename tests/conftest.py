"""Shared fixtures for the test suite."""

import pytest

from tests.factories import DocumentFactory, UserFactory, VersionFactory


@pytest.fixture
def user(db):
    """A saved instance of the configured user model."""
    return UserFactory()


@pytest.fixture
def document(db):
    """A saved :class:`Document` with an app-wide-unique generated name."""
    return DocumentFactory()


@pytest.fixture
def draft(db):
    """A saved :class:`Version`, with its owning document auto-created."""
    return VersionFactory()


@pytest.fixture
def published_version(db):
    """A saved, published :class:`Version`, with its owning document auto-created."""
    version = VersionFactory()
    version.publish()
    return version
