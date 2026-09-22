"""Tests for mvp_compliance.records."""

import dataclasses
from datetime import UTC, datetime
from unittest import mock

import pytest

from mvp_compliance.records import PersonalRecord, produce
from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    UserFactory,
    VersionFactory,
)


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

    def test_every_acceptance_of_one_document_appears(self):
        """Scenario 4; FR-002."""
        privacy = DocumentFactory(name="Privacy policy")
        v1 = VersionFactory(document=privacy)
        v1.publish()
        someone = UserFactory()
        AcceptanceFactory(user=someone, version=v1)

        v2 = VersionFactory(document=privacy)
        v2.publish()
        AcceptanceFactory(user=someone, version=v2)

        v3 = VersionFactory(document=privacy)
        v3.publish()
        AcceptanceFactory(user=someone, version=v3)

        record = produce(str(someone.pk))

        entries = record.sections[0].entries
        assert len(entries) == 3
        assert {entry.version for entry in entries} == {
            v1.number,
            v2.number,
            v3.number,
        }

    def test_a_person_with_no_records_gets_an_answer(self):
        """Scenario 5; FR-005, SC-005."""
        record = produce("nobody-the-package-has-ever-heard-of")

        assert record.is_empty is True
        assert record.sections[0].entries == ()

    def test_the_same_answer_twice(self):
        """Scenario 6; FR-006, D11: no attribute of the answer is a clock reading."""
        someone = UserFactory()
        version = VersionFactory()
        version.publish()
        AcceptanceFactory(user=someone, version=version)

        with mock.patch("django.utils.timezone.now") as now:
            now.side_effect = [
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2099, 1, 1, tzinfo=UTC),
            ]
            first = produce(str(someone.pk))
            second = produce(str(someone.pk))

        assert first == second
        assert now.call_count == 0

    def test_it_costs_a_fixed_number_of_queries(self, django_assert_num_queries):
        """SC-008: the cost does not move with the number of documents."""
        someone = UserFactory()
        for _ in range(2):
            version = VersionFactory()
            version.publish()
            AcceptanceFactory(user=someone, version=version)

        with django_assert_num_queries(1) as at_two_documents:
            produce(str(someone.pk))

        for _ in range(8):  # ten documents total
            version = VersionFactory()
            version.publish()
            AcceptanceFactory(user=someone, version=version)

        with django_assert_num_queries(1) as at_ten_documents:
            produce(str(someone.pk))

        assert len(at_two_documents.captured_queries) == len(
            at_ten_documents.captured_queries
        )

    def test_a_further_kind_of_record_would_not_change_the_answer(self):
        """FR-017: the answer's own field names are exactly ``subject`` and ``sections``,
        so a further kind of record can only join as a section.
        """
        field_names = {field.name for field in dataclasses.fields(PersonalRecord)}
        assert field_names == {"subject", "sections"}
