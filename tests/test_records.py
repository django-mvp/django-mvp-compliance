"""Tests for mvp_compliance.records."""

import pytest

from mvp_compliance.records import produce
from tests.factories import AcceptanceFactory, DocumentFactory, UserFactory, VersionFactory


@pytest.mark.django_db
class TestProduce:
    """produce() assembles the one answer this package holds about a person."""

    def test_the_answer_contains_every_acceptance_with_its_document_version_and_moment(
        self,
    ):
        """Scenarios 1, 2; FR-001, FR-002, FR-003."""
        privacy = DocumentFactory(name="Privacy policy")
        terms = DocumentFactory(name="Terms")
        privacy_v1 = VersionFactory(document=privacy)
        privacy_v1.publish()
        terms_v1 = VersionFactory(document=terms)
        terms_v1.publish()

        someone = UserFactory()
        privacy_acceptance = AcceptanceFactory(user=someone, version=privacy_v1)
        terms_acceptance = AcceptanceFactory(user=someone, version=terms_v1)

        record = produce(str(someone.pk))

        entries = record.sections[0].entries
        assert len(entries) == 2
        by_document = {entry.document: entry for entry in entries}
        assert by_document["Privacy policy"].version == privacy_v1.number
        assert (
            by_document["Privacy policy"].accepted_at
            == privacy_acceptance.accepted_at
        )
        assert by_document["Terms"].version == terms_v1.number
        assert by_document["Terms"].accepted_at == terms_acceptance.accepted_at

    def test_it_contains_nothing_belonging_to_anybody_else(self):
        """Scenario 3; FR-004, SC-001."""
        version = VersionFactory()
        version.publish()

        first = UserFactory()
        second = UserFactory()
        third = UserFactory()
        AcceptanceFactory(user=first, version=version)
        AcceptanceFactory(user=second, version=version)
        AcceptanceFactory(user=third, version=version)

        record = produce(str(second.pk))

        entries = record.sections[0].entries
        assert len(entries) == 1
        assert record.subject == str(second.pk)
