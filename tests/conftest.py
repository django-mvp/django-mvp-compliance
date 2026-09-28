"""Shared fixtures for the test suite."""

import pytest
from django.contrib.auth.models import Permission

from mvp_compliance.signals import version_published
from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    UserFactory,
    VersionFactory,
)


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def acceptance(db):
    return AcceptanceFactory()


@pytest.fixture
def document(db):
    return DocumentFactory()


@pytest.fixture
def draft(db):
    return VersionFactory()


@pytest.fixture
def published_version(db):
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
    return grant(UserFactory(is_staff=True), *DOCUMENT_WORK)


@pytest.fixture
def publisher(db):
    return grant(UserFactory(is_staff=True), *DOCUMENT_WORK, "publish_version")


@pytest.fixture
def approver(db):
    return grant(UserFactory(is_staff=True), "view_version", "publish_version")


@pytest.fixture
def disclosure_producer(db):
    return grant(UserFactory(is_staff=True), "produce_disclosure")


@pytest.fixture
def everything_else(db):
    codenames = Permission.objects.filter(
        content_type__app_label="mvp_compliance"
    ).exclude(codename="produce_disclosure")
    return grant(
        UserFactory(is_staff=True), *codenames.values_list("codename", flat=True)
    )


@pytest.fixture
def staff_without_permissions(db):
    return UserFactory(is_staff=True)


@pytest.fixture
def visitor(db):
    return UserFactory()


@pytest.fixture
def connect():
    connected = []

    def connect_receiver(receiver):
        version_published.connect(receiver, weak=False)
        connected.append(receiver)
        return receiver

    yield connect_receiver
    for receiver in connected:
        version_published.disconnect(receiver)


@pytest.fixture
def announcements(connect):
    received: list[dict] = []

    def record(sender, **kwargs):
        received.append({"sender": sender, **kwargs})

    connect(record)
    return received
