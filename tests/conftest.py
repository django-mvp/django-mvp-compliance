"""Shared fixtures for the test suite."""

import pytest
from django.contrib.auth.models import Permission

from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    UserFactory,
    VersionFactory,
)


@pytest.fixture
def user(db):
    """A saved instance of the configured user model."""
    return UserFactory()


@pytest.fixture
def acceptance(db):
    """A saved :class:`Acceptance`, with its user and version auto-created."""
    return AcceptanceFactory()


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


#: Everything the authoring surface needs short of publishing.
DOCUMENT_WORK = (
    "view_document",
    "add_document",
    "change_document",
    "delete_document",
    "view_version",
    "add_version",
    "change_version",
    "delete_version",
)


def grant(user, *codenames):
    """Give a user the named permissions on this package's models."""
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="mvp_compliance", codename__in=codenames
        )
    )
    return user


@pytest.fixture
def editor(db):
    """Somebody who may work on documents and may not publish.

    The compliance editor of the specification: every permission the
    authoring surface needs, and not ``publish_version``.
    """
    return grant(UserFactory(is_staff=True), *DOCUMENT_WORK)


@pytest.fixture
def publisher(db):
    """An editor who may also publish."""
    return grant(UserFactory(is_staff=True), *DOCUMENT_WORK, "publish_version")


@pytest.fixture
def approver(db):
    """Somebody who may publish and may not write.

    Unusual and coherent: an approver signing off wording somebody else
    prepared. It is why the two permissions are separate at all.
    """
    return grant(UserFactory(is_staff=True), "view_version", "publish_version")


@pytest.fixture
def disclosure_producer(db):
    """Staff holding only ``produce_disclosure``."""
    return grant(UserFactory(is_staff=True), "produce_disclosure")


@pytest.fixture
def everything_else(db):
    """Staff holding every permission this package defines except ``produce_disclosure``.

    Including the proxy's own routine ``view_disclosure`` — holding it
    grants nothing on its own (decisions.md D7).
    """
    codenames = Permission.objects.filter(
        content_type__app_label="mvp_compliance"
    ).exclude(codename="produce_disclosure")
    return grant(
        UserFactory(is_staff=True), *codenames.values_list("codename", flat=True)
    )


@pytest.fixture
def staff_without_permissions(db):
    """Staff who may reach the admin and hold nothing on this package."""
    return UserFactory(is_staff=True)


@pytest.fixture
def visitor(db):
    """A signed-in account that is not staff at all."""
    return UserFactory()
