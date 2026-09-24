"""Tests for mvp_compliance.records."""

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
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
from tests.test_admin import FORBIDDEN_COMPLETENESS_CLAIMS, FORBIDDEN_REGULATION_NAMES

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCLOSURE_DOCS_PATH = REPO_ROOT / "docs" / "disclosure.md"
README_PATH = REPO_ROOT / "README.md"


def readme_disclosure_section() -> str:
    """The README text this feature added: the status callout and the
    documentation list entry, not everything the README says (T055).
    """
    text = README_PATH.read_text(encoding="utf-8")
    status_start = text.index(
        "the admin's **Everything held about a person** page is what calls it"
    )
    status_end = text.index("account-area page exists yet.", status_start) + len(
        "account-area page exists yet."
    )
    doc_start = text.index("[docs/disclosure.md](docs/disclosure.md)")
    doc_end = text.index("\n- [docs/adr]", doc_start)
    return text[status_start:status_end] + "\n" + text[doc_start:doc_end]


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
            by_document["Privacy policy"].accepted_at == privacy_acceptance.accepted_at
        )
        assert by_document["Terms"].version == terms_v1.number
        assert by_document["Terms"].accepted_at == terms_acceptance.accepted_at

    def test_it_contains_nothing_belonging_to_anybody_else(self):
        """Scenario 3; FR-004, SC-001.

        Each person accepts a different document, so an entry that leaked from
        somebody else is visible rather than indistinguishable from a correct
        one.
        """
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

        with django_assert_num_queries(2) as at_two_documents:
            produce(str(someone.pk))

        for _ in range(8):  # ten documents total
            version = VersionFactory()
            version.publish()
            AcceptanceFactory(user=someone, version=version)

        with django_assert_num_queries(2) as at_ten_documents:
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


@pytest.mark.django_db
class TestNamingAPerson:
    """resolve_subject() names a person from free text (research.md R3, T020)."""

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
    """Each entry carries the wording served for the version it names (FR-007)."""

    def test_the_wording_is_what_was_stored_at_publication(self):
        """Scenarios 1, 3; FR-007, SC-002."""
        version = VersionFactory(markdown="# Privacy policy\n\nSome wording.")
        version.publish()
        someone = UserFactory()
        AcceptanceFactory(user=someone, version=version)

        record = produce(str(someone.pk))

        entry = record.sections[0].entries[0]
        assert entry.wording == version.html

    def test_a_superseded_versions_wording_is_the_superseded_one(self):
        """Scenario 2; FR-008."""
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
        """Scenario 4; FR-009."""
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
        """FR-010: the renderer is never called on this path.

        The configured renderer is switched to one that produces visibly
        different output, so an entry carrying what it would render — rather
        than what was stored at publication — is caught rather than missed.
        """
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
    """Acceptances survive the removal of the account they name (FR-014, SC-006)."""

    def test_the_answer_still_names_the_person_version_and_moment(self):
        """Scenarios 1, 2; FR-014, SC-006."""
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
        """Scenario 3."""
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
        """Scenario 4; FR-004."""
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


#: FR-015: the exact statement every answer carries, whether or not it holds
#: anything.
EXPECTED_COVERAGE_STATEMENT = (
    "This covers what this package holds about this person. The project may "
    "hold further records about them elsewhere that are not included here."
)


@pytest.mark.django_db
class TestCoverage:
    """FR-015, SC-005: every answer carries a plain statement of what it
    covers, the same whether or not anything is held.
    """

    def test_a_full_answer_carries_the_statement(self):
        """Scenario 1."""
        someone = UserFactory()
        version = VersionFactory()
        version.publish()
        AcceptanceFactory(user=someone, version=version)

        record = produce(str(someone.pk))

        assert str(record.coverage) == EXPECTED_COVERAGE_STATEMENT

    def test_an_empty_answer_carries_the_same_statement(self):
        """Scenario 2."""
        record = produce("nobody-the-package-has-ever-heard-of")

        assert record.is_empty is True
        assert str(record.coverage) == EXPECTED_COVERAGE_STATEMENT

    def test_the_documentation_claims_nothing_either(self):
        """T055, FR-016, SC-007."""
        text = (
            DISCLOSURE_DOCS_PATH.read_text(encoding="utf-8")
            + "\n"
            + readme_disclosure_section()
        ).lower()

        for name in FORBIDDEN_REGULATION_NAMES:
            assert name not in text, name
        for claim in FORBIDDEN_COMPLETENESS_CLAIMS:
            assert claim not in text, claim


@pytest.mark.django_db
class TestVersionsPublished:
    """The answer carries the versions a person published (#52)."""

    def publish_as(self, publisher, name="Privacy policy"):
        version = VersionFactory(document=DocumentFactory(name=name))
        version.publish(publisher=publisher)
        return version

    def test_every_version_they_published_is_in_its_own_section(self):
        someone = UserFactory()
        first = self.publish_as(someone, "Privacy policy")
        second = self.publish_as(someone, "Terms of use")

        record = produce(str(someone.pk))

        section = record.sections[1]
        assert str(section.heading) == "Versions published"
        assert [(entry.document, entry.version) for entry in section.entries] == [
            ("Privacy policy", first.number),
            ("Terms of use", second.number),
        ]
        assert [entry.published_at for entry in section.entries] == [
            first.published_at,
            second.published_at,
        ]

    def test_it_holds_nothing_published_by_anybody_else(self):
        someone = UserFactory()
        self.publish_as(UserFactory(), "Privacy policy")
        VersionFactory().publish()

        record = produce(str(someone.pk))

        assert record.sections[1].entries == ()
        assert record.is_empty

    def test_a_publisher_whose_account_was_removed_is_still_answered_for(self):
        departed = UserFactory()
        self.publish_as(departed)
        subject = str(departed.pk)
        departed.delete()

        record = produce(subject)

        assert [entry.document for entry in record.sections[1].entries] == [
            "Privacy policy"
        ]
        assert not record.is_empty

    def test_versions_with_no_publisher_are_never_anybody_s(self):
        """An empty subject must not match every version published by nobody."""
        VersionFactory().publish()

        record = produce("")

        assert record.sections[1].entries == ()

    def test_publishing_alone_makes_an_answer_non_empty(self):
        someone = UserFactory()
        self.publish_as(someone)

        assert not produce(str(someone.pk)).is_empty
