"""Tests for mvp_compliance.models."""

import pytest
from django.db import IntegrityError

from mvp_compliance.exceptions import PublishError
from mvp_compliance.models import Document, Version
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
