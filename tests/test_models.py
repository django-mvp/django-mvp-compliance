"""Tests for mvp_compliance.models."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.models import ProtectedError
from django.test import override_settings
from django.utils import timezone

from mvp_compliance.exceptions import (
    PublishedVersionError,
    PublishError,
    RecordedAcceptanceError,
    RecordError,
)
from mvp_compliance.models import (
    Acceptance,
    AcceptanceManager,
    AcceptanceQuerySet,
    Document,
    Version,
    VersionManager,
)
from mvp_compliance.rendering import MarkdownRenderer
from tests.factories import DocumentFactory, UserFactory, VersionFactory


class UppercaseRenderer(MarkdownRenderer):
    """A stand-in renderer that produces visibly different output."""

    def render(self, source: str) -> str:
        return super().render(source).upper()


@pytest.mark.django_db
class TestDocument:
    """A document has a lasting identity and holds no wording of its own."""

    def test_documents_exist_side_by_side_with_no_versions(self):
        privacy = Document.objects.create(name="Privacy policy")
        terms = Document.objects.create(name="Terms")
        cookies = Document.objects.create(name="Cookie policy")

        assert Document.objects.count() == 3
        assert list(privacy.versions.all()) == []
        assert list(terms.versions.all()) == []
        assert list(cookies.versions.all()) == []

    def test_duplicate_name_is_refused(self):
        Document.objects.create(name="Privacy policy")
        with pytest.raises(IntegrityError):
            Document.objects.create(name="Privacy policy")

    def test_document_holds_no_wording(self):
        field_names = {
            field.name for field in Document._meta.get_fields() if field.concrete
        }
        assert field_names == {"id", "name"}


@pytest.mark.django_db
class TestVersion:
    """Versions belong to one document and are numbered by the package."""

    def test_versions_are_numbered_in_order_independently_per_document(self):
        privacy = Document.objects.create(name="Privacy policy")
        terms = Document.objects.create(name="Terms")

        privacy_v1 = Version.objects.create(document=privacy, markdown="Privacy v1")
        terms_v1 = Version.objects.create(document=terms, markdown="Terms v1")
        privacy_v2 = Version.objects.create(document=privacy, markdown="Privacy v2")

        assert list(privacy.versions.all()) == [privacy_v1, privacy_v2]
        assert [v.number for v in privacy.versions.all()] == [1, 2]
        assert list(terms.versions.all()) == [terms_v1]
        assert [v.number for v in terms.versions.all()] == [1]

    def test_number_cannot_collide_within_a_document(self):
        privacy = Document.objects.create(name="Privacy policy")
        Version.objects.create(document=privacy, markdown="Privacy v1")

        with pytest.raises(IntegrityError):
            Version.objects.bulk_create(
                [Version(document=privacy, markdown="Privacy v2", number=1)]
            )


@pytest.mark.django_db
class TestPublishing:
    """Publishing puts exactly one version in force."""

    def test_a_new_version_is_a_draft_with_no_standing_or_publication_time(self, draft):
        assert draft.status == Version.Status.DRAFT
        assert draft.is_published is False
        assert draft.published_at is None

    def test_a_draft_has_no_stored_html(self, draft):
        assert draft.html == ""

    def test_a_draft_is_freely_editable(self, draft):
        draft.markdown = "Revised wording"
        draft.save()

        draft.refresh_from_db()
        assert draft.markdown == "Revised wording"

    def test_a_draft_is_freely_discardable(self, draft):
        pk = draft.pk

        draft.delete()

        assert not Version.objects.filter(pk=pk).exists()

    def test_publishing_the_only_draft_makes_it_current_with_no_superseded_versions(
        self, document
    ):
        version = VersionFactory(document=document)

        version.publish()

        assert version.status == Version.Status.CURRENT
        assert version.published_at is not None
        assert not document.versions.filter(status=Version.Status.SUPERSEDED).exists()

    def test_publishing_renders_the_markdown_into_html(self, document):
        version = VersionFactory(document=document, markdown="# Heading\n\nBody text.")

        version.publish()

        assert "<h1>Heading</h1>" in version.html
        assert "<p>Body text.</p>" in version.html

    def test_a_published_version_has_non_empty_stored_html(self, document):
        version = VersionFactory(document=document)

        version.publish()

        assert version.html != ""

    def test_publishing_a_draft_whose_output_is_empty_once_stripped_is_refused(
        self, document
    ):
        version = VersionFactory(document=document, markdown="   \n\n   ")

        with pytest.raises(PublishError):
            version.publish()

        version.refresh_from_db()
        assert version.status == Version.Status.DRAFT
        assert version.published_at is None
        assert version.html == ""
        assert not document.versions.filter(status=Version.Status.CURRENT).exists()

    def test_stored_html_survives_a_renderer_change(self, document):
        version = VersionFactory(document=document, markdown="Original wording")
        version.publish()
        original_html = version.html
        assert original_html != original_html.upper()

        with override_settings(
            MVP_COMPLIANCE_RENDERER="tests.test_models.UppercaseRenderer"
        ):
            version.refresh_from_db()

        assert version.html == original_html

    def test_a_draft_with_stored_html_is_refused_by_the_database(self, document):
        with pytest.raises(IntegrityError):
            Version.objects.bulk_create(
                [
                    Version(
                        document=document,
                        markdown="Draft with rendered output",
                        status=Version.Status.DRAFT,
                        published_at=None,
                        html="<p>Draft with rendered output</p>",
                    )
                ]
            )

    def test_a_published_version_with_no_stored_html_is_refused_by_the_database(
        self, document
    ):
        with pytest.raises(IntegrityError):
            Version.objects.bulk_create(
                [
                    Version(
                        document=document,
                        markdown="Published with no rendered output",
                        status=Version.Status.CURRENT,
                        published_at=timezone.now(),
                        html="",
                    )
                ]
            )

    def test_publishing_a_second_draft_becomes_current_and_supersedes_the_first(
        self, document
    ):
        first = VersionFactory(document=document)
        second = VersionFactory(document=document)
        first.publish()

        second.publish()

        first.refresh_from_db()
        assert first.status == Version.Status.SUPERSEDED
        assert second.status == Version.Status.CURRENT
        assert document.versions.filter(status=Version.Status.CURRENT).count() == 1

    def test_publishing_an_already_published_version_is_refused(self, document):
        version = VersionFactory(document=document)
        version.publish()
        published_at = version.published_at

        with pytest.raises(PublishError):
            version.publish()

        version.refresh_from_db()
        assert version.status == Version.Status.CURRENT
        assert version.published_at == published_at

    def test_status_and_published_at_must_agree(self, document):
        with pytest.raises(IntegrityError):
            Version.objects.bulk_create(
                [
                    Version(
                        document=document,
                        markdown="Draft with a publication time",
                        status=Version.Status.DRAFT,
                        published_at=timezone.now(),
                    )
                ]
            )

    def test_a_published_version_must_have_a_publication_time(self, document):
        with pytest.raises(IntegrityError):
            Version.objects.bulk_create(
                [
                    Version(
                        document=document,
                        markdown="Published with no publication time",
                        status=Version.Status.CURRENT,
                        published_at=None,
                    )
                ]
            )

    def test_second_current_row_is_refused_by_the_database(self, document):
        first = VersionFactory(document=document)
        second = VersionFactory(document=document)
        first.publish()

        with pytest.raises(IntegrityError):
            Version.objects.filter(pk=second.pk).update(
                status=Version.Status.CURRENT, published_at=timezone.now()
            )

    def test_two_publishes_leave_one_version_in_force(self, document):
        first = VersionFactory(document=document)
        second = VersionFactory(document=document)

        first.publish()
        assert document.versions.filter(status=Version.Status.CURRENT).count() == 1

        second.publish()
        assert document.versions.filter(status=Version.Status.CURRENT).count() == 1

    def test_publishing_a_version_another_process_already_published_is_refused(
        self, document
    ):
        """FR-010's refusal is about the stored row, not this instance's copy.

        Two objects loaded from the same draft is what a second process looks
        like from here. The second call must refuse the way FR-010 says it
        refuses, so a caller catching that alone does not miss it.
        """
        VersionFactory(document=document)
        first = Version.objects.get(document=document, number=1)
        stale = Version.objects.get(document=document, number=1)
        first.publish()
        published_at = first.published_at

        with pytest.raises(PublishError):
            stale.publish()

        first.refresh_from_db()
        assert first.status == Version.Status.CURRENT
        assert first.published_at == published_at
        assert document.versions.current().count() == 1

    def test_a_status_outside_the_three_standings_is_refused_by_the_database(
        self, published_version
    ):
        """Superseding is a change of standing, not a free text field (FR-013).

        The queryset guard lets ``status`` through on purpose, because that is
        how publishing supersedes. What it may become is the database's to
        say.
        """
        with pytest.raises(IntegrityError), transaction.atomic():
            Version.objects.filter(pk=published_version.pk).update(
                status="bogus-standing"
            )

        published_version.refresh_from_db()
        assert published_version.status == Version.Status.CURRENT

    def test_a_draft_cannot_be_given_a_status_outside_the_three_standings(self, draft):
        with pytest.raises(IntegrityError), transaction.atomic():
            Version.objects.filter(pk=draft.pk).update(status="bogus-standing")

        draft.refresh_from_db()
        assert draft.status == Version.Status.DRAFT

    def test_no_reverse_operation_exists(self):
        forbidden = {"unpublish", "revert", "rollback", "make_current", "restore"}

        assert not forbidden & set(dir(Version))
        assert not forbidden & set(dir(Version.objects))


@pytest.mark.django_db
class TestImmutability:
    """A published version's wording can never change (Article XII, FR-011 to FR-014)."""

    def test_saving_a_published_version_with_changed_wording_is_refused(
        self, published_version
    ):
        original_markdown = published_version.markdown
        published_version.markdown = "Tampered wording"

        with pytest.raises(PublishedVersionError):
            published_version.save()

        published_version.refresh_from_db()
        assert published_version.markdown == original_markdown

    def test_saving_a_fresh_instance_carrying_a_published_pk_is_refused(
        self, published_version
    ):
        """A guard keyed on "is this instance new" is no guard at all.

        An instance built with ``Version(...)`` has never been fetched, so
        Django reports it as being added even when its primary key names a
        stored row. The write still lands as an update.
        """
        original_markdown = published_version.markdown
        forged = Version(
            pk=published_version.pk,
            document=published_version.document,
            number=published_version.number,
            markdown="Tampered wording",
            html=published_version.html,
            status=published_version.status,
            published_at=published_version.published_at,
        )

        with pytest.raises(PublishedVersionError):
            forged.save()

        published_version.refresh_from_db()
        assert published_version.markdown == original_markdown
        assert Version.objects.filter(pk=published_version.pk).count() == 1

    def test_a_draft_still_saves_from_a_fresh_instance_carrying_its_pk(self, draft):
        """The same route on a draft is an ordinary edit and stays allowed."""
        rebuilt = Version(
            pk=draft.pk,
            document=draft.document,
            number=draft.number,
            markdown="Reworded while still a draft",
            html=draft.html,
            status=draft.status,
            published_at=draft.published_at,
        )

        rebuilt.save()

        draft.refresh_from_db()
        assert draft.markdown == "Reworded while still a draft"
        assert draft.number == rebuilt.number

    def test_updating_a_published_version_through_the_queryset_is_refused(
        self, published_version
    ):
        original_markdown = published_version.markdown

        with pytest.raises(PublishedVersionError):
            Version.objects.filter(pk=published_version.pk).update(
                markdown="Tampered wording"
            )

        published_version.refresh_from_db()
        assert published_version.markdown == original_markdown

    def test_bulk_updating_a_published_version_is_refused(self, published_version):
        original_markdown = published_version.markdown
        published_version.markdown = "Tampered wording"

        # bulk_update() wraps its internal update() in transaction.atomic(
        # savepoint=False); without our own savepoint here, the raised error
        # would leave the connection unusable for the rest of the test.
        with pytest.raises(PublishedVersionError), transaction.atomic():
            Version.objects.bulk_update([published_version], ["markdown"])

        published_version.refresh_from_db()
        assert published_version.markdown == original_markdown

    def test_published_html_cannot_be_changed(self, published_version):
        original_html = published_version.html

        published_version.html = "<p>Tampered</p>"
        with pytest.raises(PublishedVersionError):
            published_version.save()
        published_version.refresh_from_db()
        assert published_version.html == original_html

        with pytest.raises(PublishedVersionError):
            Version.objects.filter(pk=published_version.pk).update(
                html="<p>Tampered</p>"
            )
        published_version.refresh_from_db()
        assert published_version.html == original_html

        published_version.html = "<p>Tampered</p>"
        # bulk_update() wraps its internal update() in transaction.atomic(
        # savepoint=False); without our own savepoint here, the raised error
        # would leave the connection unusable for the rest of the test.
        with pytest.raises(PublishedVersionError), transaction.atomic():
            Version.objects.bulk_update([published_version], ["html"])
        published_version.refresh_from_db()
        assert published_version.html == original_html

    def test_deleting_a_published_version_instance_is_refused(self, published_version):
        original_markdown = published_version.markdown

        with pytest.raises(PublishedVersionError):
            published_version.delete()

        published_version.refresh_from_db()
        assert published_version.markdown == original_markdown

    def test_deleting_a_published_version_through_the_queryset_is_refused(
        self, published_version
    ):
        original_markdown = published_version.markdown

        with pytest.raises(PublishedVersionError):
            Version.objects.filter(pk=published_version.pk).delete()

        published_version.refresh_from_db()
        assert published_version.markdown == original_markdown

    def test_changing_only_the_status_of_a_published_version_is_permitted(
        self, published_version
    ):
        """Moving from current to superseded is what publish() does (FR-013)."""
        Version.objects.filter(pk=published_version.pk).update(
            status=Version.Status.SUPERSEDED
        )

        published_version.refresh_from_db()
        assert published_version.status == Version.Status.SUPERSEDED

    def test_superseding_does_not_change_the_wording(self, document):
        first = VersionFactory(document=document, markdown="Original wording")
        first.publish()
        original_markdown = first.markdown

        second = VersionFactory(document=document)
        second.publish()

        first.refresh_from_db()
        assert first.status == Version.Status.SUPERSEDED
        assert first.markdown == original_markdown

    def test_deleting_a_document_holding_a_version_is_refused(self, document):
        VersionFactory(document=document)

        with pytest.raises(ProtectedError):
            document.delete()

        assert Document.objects.filter(pk=document.pk).exists()

    def test_deleting_a_document_with_no_versions_succeeds(self):
        empty = DocumentFactory()
        pk = empty.pk

        empty.delete()

        assert not Document.objects.filter(pk=pk).exists()

    def test_discarding_the_only_draft_returns_the_document_to_its_empty_state(
        self, document
    ):
        draft = VersionFactory(document=document)

        draft.delete()

        assert not document.versions.exists()
        document.delete()
        assert not Document.objects.filter(pk=document.pk).exists()

    def test_correcting_an_error_makes_a_new_version(self, document):
        erroneous = VersionFactory(
            document=document, markdown="Effective date: 2026-13-45"
        )
        erroneous.publish()
        erroneous_markdown = erroneous.markdown

        correction = VersionFactory(
            document=document, markdown="Effective date: 2026-01-15"
        )
        correction.publish()

        erroneous.refresh_from_db()
        assert erroneous.status == Version.Status.SUPERSEDED
        assert erroneous.markdown == erroneous_markdown
        assert correction.status == Version.Status.CURRENT
        assert document.versions.count() == 2

    def test_the_manager_is_declared_for_use_in_migrations(self):
        """Without this, no migration ever records the manager (D10).

        Asserted on the class rather than on migration state: a recorded
        manager stays in an already-written migration even after the
        declaration is dropped, so state alone cannot see it go.
        """
        assert VersionManager.use_in_migrations is True

    def test_historical_version_model_uses_this_packages_manager(self):
        """A migration's historical model gets the same guards (D10)."""
        loader = MigrationLoader(connection)
        (leaf,) = loader.graph.leaf_nodes(app="mvp_compliance")
        state = loader.project_state(leaf)
        historical_version = state.apps.get_model("mvp_compliance", "Version")

        assert isinstance(historical_version.objects, VersionManager)


@pytest.mark.django_db
class TestRetrieval:
    """Every version stays retrievable, forever (US-5)."""

    def test_published_history_comes_back_in_order_with_drafts_absent(self, document):
        first = VersionFactory(document=document, markdown="First wording")
        first.publish()
        second = VersionFactory(document=document, markdown="Second wording")
        second.publish()
        third = VersionFactory(document=document, markdown="Third wording")
        third.publish()
        VersionFactory(document=document, markdown="An unpublished draft")

        assert list(document.versions.published()) == [first, second, third]

    def test_a_superseded_version_keeps_its_original_wording_and_html(self, document):
        first = VersionFactory(document=document, markdown="Original wording")
        first.publish()
        original_markdown = first.markdown
        original_html = first.html

        VersionFactory(document=document, markdown="Replacement wording").publish()

        first.refresh_from_db()
        assert first.status == Version.Status.SUPERSEDED
        assert first.markdown == original_markdown
        assert first.html == original_html

    def test_the_version_in_force_is_the_one_most_recently_published(self, document):
        VersionFactory(document=document, markdown="First wording").publish()
        VersionFactory(document=document, markdown="Second wording").publish()
        third = VersionFactory(document=document, markdown="Third wording")
        third.publish()

        assert document.current == third

    def test_a_document_with_nothing_published_reports_no_version_in_force(
        self, document
    ):
        assert document.current is None

        VersionFactory(document=document)

        assert document.current is None

    def test_one_version_by_its_number(self, document):
        VersionFactory(document=document, markdown="First wording")
        second = VersionFactory(document=document, markdown="Second wording")
        VersionFactory(document=document, markdown="Third wording")

        assert document.versions.get(number=2) == second

    def test_four_documents_do_not_interfere(self):
        privacy, terms, cookies, agreement = (
            DocumentFactory(),
            DocumentFactory(),
            DocumentFactory(),
            DocumentFactory(),
        )

        privacy_v1 = VersionFactory(document=privacy, markdown="Privacy v1")
        privacy_v1.publish()
        privacy_v2 = VersionFactory(document=privacy, markdown="Privacy v2")
        privacy_v2.publish()

        terms_v1 = VersionFactory(document=terms, markdown="Terms v1")
        terms_v1.publish()

        VersionFactory(document=cookies, markdown="Cookies draft")

        agreement_v1 = VersionFactory(document=agreement, markdown="Agreement v1")
        agreement_v1.publish()
        agreement_v2 = VersionFactory(document=agreement, markdown="Agreement v2")
        agreement_v2.publish()
        agreement_v3 = VersionFactory(document=agreement, markdown="Agreement v3")
        agreement_v3.publish()

        assert [v.number for v in privacy.versions.all()] == [1, 2]
        assert privacy.current == privacy_v2
        assert list(privacy.versions.published()) == [privacy_v1, privacy_v2]

        assert [v.number for v in terms.versions.all()] == [1]
        assert terms.current == terms_v1
        assert list(terms.versions.published()) == [terms_v1]

        assert [v.number for v in cookies.versions.all()] == [1]
        assert cookies.current is None
        assert list(cookies.versions.published()) == []

        assert [v.number for v in agreement.versions.all()] == [1, 2, 3]
        assert agreement.current == agreement_v3
        assert list(agreement.versions.published()) == [
            agreement_v1,
            agreement_v2,
            agreement_v3,
        ]


@pytest.mark.django_db
class TestAcceptance:
    """Recording an acceptance names a user, a version and a moment (FR-001)."""

    def test_recording_creates_a_record_naming_the_user_version_and_moment(
        self, user, published_version
    ):
        acceptance = Acceptance.objects.record(user, published_version)

        assert acceptance.user == user
        assert acceptance.version == published_version
        assert acceptance.accepted_at is not None

        field_names = {
            field.name for field in Acceptance._meta.get_fields() if field.concrete
        }
        assert field_names == {
            "id",
            "user",
            "subject",
            "version",
            "accepted_at",
            "ip_address",
        }

    def test_no_way_to_accept_a_document(self, user, document):
        field_names = {field.name for field in Acceptance._meta.get_fields()}
        assert "document" not in field_names
        assert not hasattr(Acceptance.objects, "record_for_document")

        with pytest.raises(AttributeError):
            Acceptance.objects.record(user, document)

    def test_record_still_points_at_the_version_it_named(self, user, document):
        first = VersionFactory(document=document)
        first.publish()
        acceptance = Acceptance.objects.record(user, first)

        second = VersionFactory(document=document)
        second.publish()

        acceptance.refresh_from_db()
        assert acceptance.version == first
        assert acceptance.version.status == Version.Status.SUPERSEDED


@pytest.mark.django_db
class TestRecording:
    """``record()`` refuses a draft version and a user with no primary key (FR-003, D2)."""

    def test_recording_against_a_never_published_version_is_refused(self, user, draft):
        with pytest.raises(RecordError):
            Acceptance.objects.record(user, draft)

        assert not Acceptance.objects.exists()

    def test_recording_against_a_superseded_version_is_accepted(self, user, document):
        first = VersionFactory(document=document)
        first.publish()
        second = VersionFactory(document=document)
        second.publish()
        first.refresh_from_db()
        assert first.status == Version.Status.SUPERSEDED

        acceptance = Acceptance.objects.record(user, first)

        assert acceptance.version == first

    def test_recording_for_a_user_with_no_primary_key_is_refused(
        self, published_version
    ):
        unsaved_user = get_user_model()(username="not-saved")

        with pytest.raises(RecordError):
            Acceptance.objects.record(unsaved_user, published_version)

        assert not Acceptance.objects.exists()

    def test_accepting_a_later_version_of_the_same_document_creates_a_second_record(
        self, user, document
    ):
        """Scenario 1, FR-008, SC-002: three records, and the first two are unchanged."""
        first_version = VersionFactory(document=document)
        first_version.publish()
        first = Acceptance.objects.record(user, first_version)
        first_accepted_at = first.accepted_at

        second_version = VersionFactory(document=document)
        second_version.publish()
        second = Acceptance.objects.record(user, second_version)
        second_accepted_at = second.accepted_at

        third_version = VersionFactory(document=document)
        third_version.publish()
        Acceptance.objects.record(user, third_version)

        first.refresh_from_db()
        assert first.version == first_version
        assert first.accepted_at == first_accepted_at

        second.refresh_from_db()
        assert second.version == second_version
        assert second.accepted_at == second_accepted_at

        assert (
            Acceptance.objects.filter(subject=Acceptance.subject_of(user)).count() == 3
        )

    def test_acceptances_are_listed_in_the_order_they_happened(
        self, user, document, monkeypatch
    ):
        """Scenario 2, FR-008: listed in the order they happened, not the order of their rows."""
        later_version = VersionFactory(document=document)
        later_version.publish()
        earlier_version = VersionFactory(document=document)
        earlier_version.publish()

        later_moment = timezone.now()
        earlier_moment = later_moment - timedelta(minutes=5)

        monkeypatch.setattr(timezone, "now", lambda: later_moment)
        later = Acceptance.objects.record(user, later_version)

        monkeypatch.setattr(timezone, "now", lambda: earlier_moment)
        earlier = Acceptance.objects.record(user, earlier_version)

        ordered = list(Acceptance.objects.filter(subject=Acceptance.subject_of(user)))
        assert ordered == [earlier, later]

    def test_two_people_accepting_the_same_version_each_get_their_own_record(
        self, published_version
    ):
        """Scenario 4, FR-008: neither person's record can be mistaken for the other's."""
        alice = UserFactory()
        bob = UserFactory()

        alice_acceptance = Acceptance.objects.record(alice, published_version)
        bob_acceptance = Acceptance.objects.record(bob, published_version)

        assert alice_acceptance.subject != bob_acceptance.subject
        assert Acceptance.objects.filter(version=published_version).count() == 2

    def test_the_same_version_twice_leaves_one_record(self, user, published_version):
        """Scenario 3, FR-009, D3: a repeat succeeds and returns the record that already exists."""
        first = Acceptance.objects.record(user, published_version)

        again = Acceptance.objects.record(user, published_version)

        assert again == first
        assert (
            Acceptance.objects.filter(
                subject=Acceptance.subject_of(user), version=published_version
            ).count()
            == 1
        )

    def test_a_second_row_is_refused_by_the_database(self, user, published_version):
        """The constraint holds even for a row that bypasses record() (FR-009)."""
        Acceptance.objects.record(user, published_version)

        with pytest.raises(IntegrityError):
            Acceptance.objects.bulk_create(
                [
                    Acceptance(
                        user=user,
                        subject=Acceptance.subject_of(user),
                        version=published_version,
                        accepted_at=timezone.now(),
                    )
                ]
            )

    def test_two_recordings_leave_one_record(
        self, user, published_version, monkeypatch
    ):
        """Scenario 5, FR-010, SC-003: the constraint's IntegrityError path
        returns the winner's row without raising, deterministically and
        without threads or wall-clock timing.

        The first lookup is genuine and finds nothing, exactly like an
        uncontended call. As a side effect of that miss, it inserts and
        commits a competing row as a sibling operation rather than a nested
        one, so it survives when record()'s own create() collides on the
        constraint and its own attempt is rolled back — the same interleaving
        two genuinely concurrent attempts would produce.
        """
        subject = Acceptance.subject_of(user)
        original_get = AcceptanceQuerySet.get
        seen_a_lookup = []

        def get_with_a_concurrent_writer_on_the_first_miss(self, *args, **kwargs):
            if seen_a_lookup:
                return original_get(self, *args, **kwargs)
            seen_a_lookup.append(True)
            try:
                return original_get(self, *args, **kwargs)
            except Acceptance.DoesNotExist:
                with transaction.atomic():
                    Acceptance(
                        user=user,
                        subject=subject,
                        version=published_version,
                        accepted_at=timezone.now(),
                    ).save()
                raise

        monkeypatch.setattr(
            AcceptanceQuerySet, "get", get_with_a_concurrent_writer_on_the_first_miss
        )

        acceptance = Acceptance.objects.record(user, published_version)

        assert acceptance.subject == subject
        assert (
            Acceptance.objects.filter(
                subject=subject, version=published_version
            ).count()
            == 1
        )


@pytest.mark.django_db
class TestAcceptanceImmutability:
    """An acceptance, once written, cannot be changed or deleted (Article XII, FR-004 to FR-006)."""

    def test_saving_an_existing_row_is_refused(self, user, published_version):
        acceptance = Acceptance.objects.record(user, published_version)
        original_subject = acceptance.subject

        acceptance.subject = "tampered"
        with pytest.raises(RecordedAcceptanceError):
            acceptance.save()

        acceptance.refresh_from_db()
        assert acceptance.subject == original_subject

    def test_updating_through_the_queryset_is_refused(self, user, published_version):
        acceptance = Acceptance.objects.record(user, published_version)
        original_subject = acceptance.subject

        with pytest.raises(RecordedAcceptanceError):
            Acceptance.objects.filter(pk=acceptance.pk).update(subject="tampered")

        acceptance.refresh_from_db()
        assert acceptance.subject == original_subject

    def test_bulk_update_is_refused(self, user, published_version):
        acceptance = Acceptance.objects.record(user, published_version)
        original_subject = acceptance.subject
        acceptance.subject = "tampered"

        # bulk_update() wraps its internal update() in transaction.atomic(
        # savepoint=False); without our own savepoint here, the raised error
        # would leave the connection unusable for the rest of the test.
        with pytest.raises(RecordedAcceptanceError), transaction.atomic():
            Acceptance.objects.bulk_update([acceptance], ["subject"])

        acceptance.refresh_from_db()
        assert acceptance.subject == original_subject

    def test_deleting_the_instance_is_refused(self, user, published_version):
        acceptance = Acceptance.objects.record(user, published_version)

        with pytest.raises(RecordedAcceptanceError):
            acceptance.delete()

        assert Acceptance.objects.filter(pk=acceptance.pk).exists()

    def test_deleting_through_the_queryset_is_refused(self, user, published_version):
        acceptance = Acceptance.objects.record(user, published_version)

        with pytest.raises(RecordedAcceptanceError):
            Acceptance.objects.filter(pk=acceptance.pk).delete()

        assert Acceptance.objects.filter(pk=acceptance.pk).exists()

    def test_a_historical_model_inherits_the_guard(self):
        """A migration's historical model gets the same guards (scenario 3, FR-004)."""
        loader = MigrationLoader(connection)
        (leaf,) = loader.graph.leaf_nodes(app="mvp_compliance")
        state = loader.project_state(leaf)
        historical_acceptance = state.apps.get_model("mvp_compliance", "Acceptance")

        assert isinstance(historical_acceptance.objects, AcceptanceManager)
