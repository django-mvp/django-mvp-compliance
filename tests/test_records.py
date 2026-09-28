"""Tests for mvp_compliance.records."""

import dataclasses
from datetime import UTC, datetime
from unittest import mock

import pytest
from django.test import override_settings

from mvp_compliance.records import PersonalRecord, produce, resolve_subject
from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    UserFactory,
    VersionFactory,
)


@pytest.mark.django_db
class TestProduce:
    def test_the_answer_contains_every_acceptance_with_its_document_version_and_moment(
        self,
    ):
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
            by_document["Privacy policy"].accepted_at == privacy_acceptance.accepted_at
        )
        assert by_document["Terms"].version == terms_v1.number
        assert by_document["Terms"].accepted_at == terms_acceptance.accepted_at

    def test_it_contains_nothing_belonging_to_anybody_else(self):
        people_and_documents = {}
        for name in ("Privacy policy", "Terms", "Cookie policy"):
            document = DocumentFactory(name=name)
            version = VersionFactory(document=document)
            version.publish()
            person = UserFactory()
            AcceptanceFactory(user=person, version=version)
            people_and_documents[name] = person

        second = people_and_documents["Terms"]
        record = produce(str(second.pk))

        entries = record.sections[0].entries
        assert record.subject == str(second.pk)
        assert [entry.document for entry in entries] == ["Terms"]

    def test_every_acceptance_of_one_document_appears(self):
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
        record = produce("nobody-the-package-has-ever-heard-of")

        assert record.is_empty is True
        assert record.sections[0].entries == ()

    def test_the_same_answer_twice(self):
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
        field_names = {field.name for field in dataclasses.fields(PersonalRecord)}
        assert field_names == {"subject", "sections"}


@pytest.mark.django_db
class TestNamingAPerson:
    def test_an_accounts_login_name_resolves_to_its_identifier(self):
        someone = UserFactory(username="alice")

        assert resolve_subject("alice") == str(someone.pk)

    def test_an_accounts_email_resolves_to_its_identifier(self):
        someone = UserFactory(email="alice@example.com")

        assert resolve_subject("alice@example.com") == str(someone.pk)

    def test_an_email_match_is_case_insensitive(self):
        someone = UserFactory(email="alice@example.com")

        assert resolve_subject("ALICE@EXAMPLE.COM") == str(someone.pk)

    def test_text_matching_neither_resolves_to_itself(self):
        assert (
            resolve_subject("nobody-the-package-has-ever-heard-of")
            == "nobody-the-package-has-ever-heard-of"
        )


@pytest.mark.django_db
class TestWording:
    def test_the_wording_is_what_was_stored_at_publication(self):
        version = VersionFactory(markdown="# Privacy policy\n\nSome wording.")
        version.publish()
        someone = UserFactory()
        AcceptanceFactory(user=someone, version=version)

        record = produce(str(someone.pk))

        entry = record.sections[0].entries[0]
        assert entry.wording == version.html

    def test_a_superseded_versions_wording_is_the_superseded_one(self):
        document = DocumentFactory()
        v1 = VersionFactory(document=document, markdown="Original wording")
        v1.publish()
        someone = UserFactory()
        AcceptanceFactory(user=someone, version=v1)

        v2 = VersionFactory(document=document, markdown="Revised wording")
        v2.publish()

        record = produce(str(someone.pk))

        entry = record.sections[0].entries[0]
        assert entry.wording == v1.html
        assert entry.wording != v2.html

    def test_each_entry_carries_its_own_versions_wording(self):
        document = DocumentFactory()
        someone = UserFactory()
        versions = []
        for n in range(3):
            version = VersionFactory(document=document, markdown=f"Wording {n}")
            version.publish()
            AcceptanceFactory(user=someone, version=version)
            versions.append(version)

        record = produce(str(someone.pk))

        entries = record.sections[0].entries
        assert len(entries) == 3
        by_version_number = {entry.version: entry for entry in entries}
        for version in versions:
            assert by_version_number[version.number].wording == version.html

    def test_nothing_is_rendered_when_an_answer_is_produced(self):
        version = VersionFactory(markdown="# Privacy policy\n\nSome wording.")
        version.publish()
        stored_html = version.html
        someone = UserFactory()
        AcceptanceFactory(user=someone, version=version)

        with override_settings(
            MVP_COMPLIANCE_RENDERER="tests.test_models.UppercaseRenderer"
        ):
            record = produce(str(someone.pk))

        entry = record.sections[0].entries[0]
        assert entry.wording == stored_html
        assert entry.wording != stored_html.upper()


@pytest.mark.django_db
class TestSurvivingRecords:
    def test_the_answer_still_names_the_person_version_and_moment(self):
        someone = UserFactory()
        version = VersionFactory(document=DocumentFactory(name="Privacy policy"))
        version.publish()
        acceptance = AcceptanceFactory(user=someone, version=version)
        subject = acceptance.subject

        someone.delete()

        record = produce(subject)

        entries = record.sections[0].entries
        assert len(entries) == 1
        entry = entries[0]
        assert record.subject == subject
        assert entry.document == "Privacy policy"
        assert entry.version == version.number
        assert entry.accepted_at == acceptance.accepted_at
        assert entry.wording == version.html

    def test_the_other_setting_leaves_nothing_to_produce(self):
        someone = UserFactory()
        version = VersionFactory()
        version.publish()
        acceptance = AcceptanceFactory(user=someone, version=version)
        subject = acceptance.subject

        with override_settings(
            MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL=False
        ):
            someone.delete()

        record = produce(subject)

        assert record.is_empty is True

    def test_a_mix_of_people_with_and_without_accounts(self):
        gone = UserFactory()
        gone_version = VersionFactory(document=DocumentFactory(name="Gone's document"))
        gone_version.publish()
        gone_acceptance = AcceptanceFactory(user=gone, version=gone_version)
        gone_subject = gone_acceptance.subject
        gone.delete()

        still_here = UserFactory()
        still_here_version = VersionFactory(
            document=DocumentFactory(name="Still here's document")
        )
        still_here_version.publish()
        AcceptanceFactory(user=still_here, version=still_here_version)

        record = produce(gone_subject)

        entries = record.sections[0].entries
        assert record.subject == gone_subject
        assert [entry.document for entry in entries] == ["Gone's document"]


@pytest.mark.django_db
class TestCoverage:
    def test_a_full_and_an_empty_answer_carry_the_same_statement(self):
        someone = UserFactory()
        version = VersionFactory()
        version.publish()
        AcceptanceFactory(user=someone, version=version)

        full = produce(str(someone.pk))
        empty = produce("nobody-the-package-has-ever-heard-of")

        assert not full.is_empty
        assert empty.is_empty
        assert str(full.coverage)
        assert str(full.coverage) == str(empty.coverage)
