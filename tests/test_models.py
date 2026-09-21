"""Tests for mvp_compliance.models."""

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.utils import timezone

from mvp_compliance.exceptions import PublishedVersionError, PublishError
from mvp_compliance.models import Document, Version, VersionManager
from tests.factories import VersionFactory


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

    def test_historical_version_model_uses_this_packages_manager(self):
        """A migration's historical model gets the same guards (D10)."""
        loader = MigrationLoader(connection)
        (leaf,) = loader.graph.leaf_nodes(app="mvp_compliance")
        state = loader.project_state(leaf)
        historical_version = state.apps.get_model("mvp_compliance", "Version")

        assert isinstance(historical_version.objects, VersionManager)
