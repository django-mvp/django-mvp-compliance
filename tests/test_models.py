"""Tests for mvp_compliance.models."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.models import ProtectedError, QuerySet
from django.test import RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from mvp_compliance.exceptions import (
    DeclaredDocumentError,
    PublishedTranslationError,
    PublishedVersionError,
    PublishError,
    RecordedAcceptanceError,
    RecordError,
    TranslationError,
)
from mvp_compliance.models import (
    Acceptance,
    AcceptanceManager,
    AcceptanceQuerySet,
    Document,
    Translation,
    Version,
    VersionManager,
    keep_or_remove_acceptances,
    language_name,
    offered_languages,
)
from mvp_compliance.records import produce
from mvp_compliance.rendering import MarkdownRenderer
from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    TranslationFactory,
    UserFactory,
    VersionFactory,
)


class UppercaseRenderer(MarkdownRenderer):
    """A stand-in renderer that produces visibly different output."""

    def render(self, source: str) -> str:
        return super().render(source).upper()


MODEL_FIELDS = [
    pytest.param(field, id=f"{model.__name__}.{field.name}")
    for model in apps.get_app_config("mvp_compliance").get_models()
    for field in model._meta.get_fields()
    if field.concrete and not field.auto_created
]


class TestModelFields:
    @pytest.mark.parametrize("field", MODEL_FIELDS)
    def test_every_field_has_a_verbose_name_and_help_text(self, field):
        assert field.verbose_name
        assert field.help_text


@pytest.mark.django_db
class TestDocument:
    def test_documents_exist_side_by_side_with_no_versions(self):
        privacy = Document.objects.create(name="Privacy policy", slug="privacy-policy")
        terms = Document.objects.create(name="Terms", slug="terms")
        cookies = Document.objects.create(name="Cookie policy", slug="cookie-policy")

        assert Document.objects.count() == 3
        assert list(privacy.versions.all()) == []
        assert list(terms.versions.all()) == []
        assert list(cookies.versions.all()) == []

    def test_duplicate_name_is_refused(self):
        Document.objects.create(name="Privacy policy", slug="privacy-policy")
        with pytest.raises(IntegrityError):
            Document.objects.create(name="Privacy policy", slug="privacy")

    def test_document_holds_no_wording(self):
        field_names = {
            field.name for field in Document._meta.get_fields() if field.concrete
        }
        assert field_names == {"id", "name", "slug", "kind", "enforced"}


@pytest.mark.django_db
class TestDocumentKind:
    def test_a_document_created_without_a_kind_is_one_people_agree_to(self):
        document = Document.objects.create(name="Privacy policy", slug="privacy-policy")

        document.refresh_from_db()

        assert document.kind == Document.Kind.AGREED

    def test_a_document_created_as_a_notice_keeps_it(self):
        document = DocumentFactory(kind=Document.Kind.NOTICE)

        document.refresh_from_db()

        assert document.kind == Document.Kind.NOTICE


@pytest.mark.django_db
class TestDocumentSlug:
    """A document's slug is its identifier in an address, and no two share one."""

    def test_a_document_saves_with_a_slug(self):
        document = Document.objects.create(name="Privacy policy", slug="privacy-policy")

        document.refresh_from_db()
        assert document.slug == "privacy-policy"

    def test_two_documents_with_the_same_slug_are_refused(self):
        Document.objects.create(name="Privacy policy", slug="privacy")
        with pytest.raises(IntegrityError):
            Document.objects.create(name="Privacy notice", slug="privacy")

    def test_the_slug_says_what_it_is_for(self):
        field = Document._meta.get_field("slug")

        assert str(field.verbose_name)
        assert str(field.help_text)

    @pytest.mark.parametrize(
        "slug", ["Privacy", "privacy_policy", "-privacy", "privacy-"]
    )
    def test_a_slug_with_capitals_underscores_or_a_stray_hyphen_is_invalid(self, slug):
        document = Document(name="Privacy policy", slug=slug)

        with pytest.raises(ValidationError) as error:
            document.full_clean()

        assert "slug" in error.value.message_dict

    def test_lowercase_letters_digits_and_inner_hyphens_are_valid(self):
        document = Document(name="Privacy policy", slug="privacy-policy-2")

        document.full_clean()

    def test_the_slug_changes_freely_while_nothing_is_published(self):
        document = Document.objects.create(name="Privacy policy", slug="privacy")
        VersionFactory(document=document)

        document.slug = "privacy-policy"
        document.save()
        Document.objects.filter(pk=document.pk).update(slug="privacy-notice")

        document.refresh_from_db()
        assert document.slug == "privacy-notice"

    def test_saving_a_new_slug_after_publication_is_refused(self):
        document = Document.objects.create(name="Privacy policy", slug="privacy")
        VersionFactory(document=document).publish()

        document.slug = "privacy-policy"
        with pytest.raises(PublishedVersionError):
            document.save()

        document.refresh_from_db()
        assert document.slug == "privacy"

    def test_updating_the_slug_after_publication_is_refused(self):
        document = Document.objects.create(name="Privacy policy", slug="privacy")
        VersionFactory(document=document).publish()

        with pytest.raises(PublishedVersionError):
            Document.objects.filter(pk=document.pk).update(slug="privacy-policy")

        document.refresh_from_db()
        assert document.slug == "privacy"

    def test_bulk_updating_the_slug_after_publication_is_refused(self):
        document = Document.objects.create(name="Privacy policy", slug="privacy")
        VersionFactory(document=document).publish()

        document.slug = "privacy-policy"
        # bulk_update() wraps its internal update() in transaction.atomic(
        # savepoint=False), so the test supplies the savepoint.
        with pytest.raises(PublishedVersionError), transaction.atomic():
            Document.objects.bulk_update([document], ["slug"])

        document.refresh_from_db()
        assert document.slug == "privacy"

    def test_a_superseded_version_still_fixes_the_slug(self):
        document = Document.objects.create(name="Privacy policy", slug="privacy")
        VersionFactory(document=document, markdown="One").publish()
        VersionFactory(document=document, markdown="Two").publish()

        with pytest.raises(PublishedVersionError):
            Document.objects.filter(pk=document.pk).update(slug="other")

    def test_saving_an_unchanged_slug_after_publication_is_allowed(self):
        document = Document.objects.create(name="Privacy policy", slug="privacy")
        VersionFactory(document=document).publish()

        document.name = "Privacy notice"
        document.save()

        document.refresh_from_db()
        assert document.name == "Privacy notice"
        assert document.slug == "privacy"

    def test_a_save_that_does_not_write_the_slug_is_allowed(self):
        document = Document.objects.create(name="Privacy policy", slug="privacy")
        VersionFactory(document=document).publish()

        document.slug = "privacy-notice"
        document.name = "Privacy notice"
        document.save(update_fields=["name"])

        document.refresh_from_db()
        assert document.name == "Privacy notice"
        assert document.slug == "privacy"

    def test_the_name_changes_after_publication_and_the_pages_keep_their_address(
        self, client
    ):
        document = Document.objects.create(name="Privacy policy", slug="privacy")
        VersionFactory(document=document).publish()
        address = reverse("mvp_compliance:document", args=["privacy"])

        Document.objects.filter(pk=document.pk).update(name="Privacy notice")

        response = client.get(address)
        assert response.status_code == 200
        assert "Privacy notice" in response.content.decode()


@pytest.mark.django_db
class TestDeclaredSlug:
    """US-2 scenarios 2-4, FR-011 to FR-013: a declared slug is fixed from the
    start, before any version is published.
    """

    @pytest.fixture
    def declared(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = {"privacy-policy": "Privacy policy"}
        return Document.objects.create(name="Privacy policy", slug="privacy-policy")

    def test_save_refuses_a_new_slug_and_leaves_the_stored_slug(self, declared):
        declared.slug = "privacy"

        with pytest.raises(DeclaredDocumentError):
            declared.save()

        assert Document.objects.get(pk=declared.pk).slug == "privacy-policy"

    def test_update_refuses_a_new_slug_and_leaves_the_stored_slug(self, declared):
        with pytest.raises(DeclaredDocumentError):
            Document.objects.filter(pk=declared.pk).update(slug="privacy")

        assert Document.objects.get(pk=declared.pk).slug == "privacy-policy"

    def test_bulk_update_refuses_a_new_slug_and_leaves_the_stored_slug(self, declared):
        declared.slug = "privacy"

        # bulk_update() wraps its internal update() in transaction.atomic(
        # savepoint=False), so the test supplies the savepoint.
        with pytest.raises(DeclaredDocumentError), transaction.atomic():
            Document.objects.bulk_update([declared], ["slug"])

        assert Document.objects.get(pk=declared.pk).slug == "privacy-policy"

    def test_save_with_the_same_slug_is_allowed(self, declared):
        declared.name = "Privacy"

        declared.save()

        assert Document.objects.get(pk=declared.pk).name == "Privacy"

    def test_name_kind_and_enforced_still_change_through_save(self, declared):
        declared.name = "Privacy"
        declared.kind = Document.Kind.NOTICE
        declared.enforced = False

        declared.save()

        declared = Document.objects.get(pk=declared.pk)
        assert declared.name == "Privacy"
        assert declared.kind == Document.Kind.NOTICE
        assert not declared.enforced

    def test_name_kind_and_enforced_still_change_through_update(self, declared):
        Document.objects.filter(pk=declared.pk).update(
            name="Privacy", kind=Document.Kind.NOTICE, enforced=False
        )

        declared = Document.objects.get(pk=declared.pk)
        assert declared.name == "Privacy"
        assert declared.kind == Document.Kind.NOTICE
        assert not declared.enforced

    def test_update_refuses_a_queryset_holding_any_declared_slug(self, declared):
        other = DocumentFactory()

        with pytest.raises(DeclaredDocumentError):
            Document.objects.filter(pk__in=[declared.pk, other.pk]).update(
                slug="shared"
            )

        assert Document.objects.get(pk=other.pk).slug == other.slug

    def test_an_undeclared_document_without_a_version_changes_its_slug(self, declared):
        other = DocumentFactory()
        other.slug = "elsewhere"

        other.save()

        assert Document.objects.get(pk=other.pk).slug == "elsewhere"

    def test_a_declared_slug_is_refused_before_the_published_check(self, declared):
        VersionFactory(document=declared).publish()
        declared.slug = "privacy"

        with pytest.raises(DeclaredDocumentError):
            declared.save()
        with pytest.raises(DeclaredDocumentError):
            Document.objects.filter(pk=declared.pk).update(slug="privacy")

    def test_a_published_slug_is_still_refused_once_the_declaration_is_removed(
        self, declared, settings
    ):
        VersionFactory(document=declared).publish()
        settings.MVP_COMPLIANCE_DOCUMENTS = {}
        declared.slug = "privacy"

        with pytest.raises(PublishedVersionError):
            declared.save()

    def test_with_the_declaration_removed_the_slug_changes_again(
        self, declared, settings
    ):
        settings.MVP_COMPLIANCE_DOCUMENTS = {}
        declared.slug = "privacy"

        declared.save()

        assert Document.objects.get(pk=declared.pk).slug == "privacy"

    def test_a_declared_notice_is_outstanding_for_nobody_after_publication(
        self, declared, user
    ):
        declared.kind = Document.Kind.NOTICE
        declared.save()

        VersionFactory(document=declared).publish()

        assert declared not in Document.objects.outstanding_for(user)
        assert declared not in Document.objects.enforced_outstanding_for(user)


@pytest.mark.django_db
class TestReservedSlug:
    """US-3 scenario 4, FR-014: the slug of the list of agreed documents is not available."""

    def test_the_slug_of_the_list_is_refused_with_the_reserved_code(self):
        document = Document(name="Agreed", slug="agreed")

        with pytest.raises(ValidationError) as error:
            document.full_clean()

        assert [e.code for e in error.value.error_dict["slug"]] == ["reserved"]

    @pytest.mark.parametrize("slug", ["agreed-terms", "agree-to-terms", "not-agreed"])
    def test_a_slug_that_only_contains_the_reserved_one_is_valid(self, slug):
        Document(name="Terms", slug=slug).full_clean()

    def test_the_slug_of_the_page_a_person_downloads_their_data_from_is_refused(self):
        document = Document(name="Data", slug="data")

        with pytest.raises(ValidationError) as error:
            document.full_clean()

        assert [e.code for e in error.value.error_dict["slug"]] == ["reserved"]

    @pytest.mark.parametrize("slug", ["delete", "deleted"])
    def test_the_slugs_of_the_pages_for_deleting_an_account_are_refused(self, slug):
        document = Document(name="Delete", slug=slug)

        with pytest.raises(ValidationError) as error:
            document.full_clean()

        assert [e.code for e in error.value.error_dict["slug"]] == ["reserved"]

    def test_the_slug_of_the_page_that_asks_is_refused_with_the_reserved_code(self):
        document = Document(name="Agree", slug="agree")

        with pytest.raises(ValidationError) as error:
            document.full_clean()

        assert [e.code for e in error.value.error_dict["slug"]] == ["reserved"]


@pytest.mark.django_db
class TestDocumentInForce:
    """Only a document with a version in force is one a visitor can read."""

    def test_returns_documents_with_a_current_version_carrying_it(self):
        document = DocumentFactory()
        version = VersionFactory(document=document)
        version.publish()

        found = list(Document.objects.in_force())

        assert found == [document]
        assert [v.pk for v in found[0].current_versions] == [version.pk]

    def test_excludes_a_document_with_only_drafts(self):
        VersionFactory(document=DocumentFactory())

        assert list(Document.objects.in_force()) == []

    def test_excludes_a_document_with_no_versions(self):
        DocumentFactory()

        assert list(Document.objects.in_force()) == []

    def test_a_superseded_version_is_not_the_one_carried(self):
        document = DocumentFactory()
        first = VersionFactory(document=document)
        first.publish()
        second = VersionFactory(document=document)
        second.publish()

        (found,) = Document.objects.in_force()

        assert [v.pk for v in found.current_versions] == [second.pk]


@pytest.mark.django_db
class TestWithReplacedAt:
    """A version knows when the next published version of its document replaced it."""

    def test_is_the_next_published_versions_date_and_none_for_the_current_one(self):
        document = DocumentFactory()
        first, second, third = (VersionFactory(document=document) for _ in range(3))
        for version in (first, second, third):
            version.publish()
        other = VersionFactory(document=DocumentFactory())
        other.publish()

        found = {v.pk: v for v in Version.objects.published().with_replaced_at()}

        second.refresh_from_db()
        third.refresh_from_db()
        assert found[first.pk].replaced_at == second.published_at
        assert found[second.pk].replaced_at == third.published_at
        assert found[third.pk].replaced_at is None
        assert found[other.pk].replaced_at is None

    def test_a_draft_is_not_a_replacement(self):
        document = DocumentFactory()
        first = VersionFactory(document=document)
        first.publish()
        VersionFactory(document=document)

        (found,) = Version.objects.published().with_replaced_at()

        assert found.pk == first.pk
        assert found.replaced_at is None

    def test_annotates_every_version_in_one_query(self, django_assert_num_queries):
        document = DocumentFactory()
        for _ in range(4):
            VersionFactory(document=document).publish()

        with django_assert_num_queries(1):
            assert [
                v.replaced_at for v in Version.objects.published().with_replaced_at()
            ]


@pytest.mark.django_db
class TestSinceLastAcceptedBy:
    """The versions of a document published after the last one a person accepted."""

    def test_names_the_versions_published_after_the_one_accepted(self, user):
        document = DocumentFactory()
        first, second, third = (VersionFactory(document=document) for _ in range(3))
        first.publish()
        Acceptance.objects.record(user, first)
        second.publish()
        third.publish()

        found = Version.objects.published().since_last_accepted_by(user)

        assert set(found) == {second, third}

    def test_counts_from_the_latest_version_accepted(self, user):
        document = DocumentFactory()
        first, second, third = (VersionFactory(document=document) for _ in range(3))
        first.publish()
        Acceptance.objects.record(user, first)
        second.publish()
        Acceptance.objects.record(user, second)
        third.publish()

        found = Version.objects.published().since_last_accepted_by(user)

        assert list(found) == [third]

    def test_names_nothing_of_a_document_never_accepted(self, user):
        document = DocumentFactory()
        for _ in range(2):
            VersionFactory(document=document).publish()

        found = Version.objects.published().since_last_accepted_by(user)

        assert list(found) == []

    def test_another_persons_acceptance_does_not_count(self, user):
        document = DocumentFactory()
        first, second = (VersionFactory(document=document) for _ in range(2))
        first.publish()
        Acceptance.objects.record(UserFactory(), first)
        second.publish()

        found = Version.objects.published().since_last_accepted_by(user)

        assert list(found) == []

    def test_each_document_counts_from_its_own_acceptance(self, user):
        accepted_late = DocumentFactory()
        accepted_early = DocumentFactory()
        early = VersionFactory(document=accepted_early)
        early.publish()
        Acceptance.objects.record(user, early)
        late = VersionFactory(document=accepted_late)
        late.publish()
        Acceptance.objects.record(user, late)
        after_early = VersionFactory(document=accepted_early)
        after_early.publish()

        found = Version.objects.published().since_last_accepted_by(user)

        assert list(found) == [after_early]


@pytest.mark.django_db
class TestSummary:
    """A version's summary of what changed is part of it, and frozen at publication."""

    def test_a_drafts_summary_can_be_written_and_rewritten(self, draft):
        draft.summary = "First attempt"
        draft.save()
        Version.objects.filter(pk=draft.pk).update(summary="Second attempt")

        draft.refresh_from_db()
        assert draft.summary == "Second attempt"

    def test_the_summary_written_as_a_draft_is_published_with_it(self):
        version = VersionFactory(summary="We now keep the address you sign in with.")

        version.publish()

        version.refresh_from_db()
        assert version.summary == "We now keep the address you sign in with."

    def test_a_version_is_published_with_no_summary(self, published_version):
        assert published_version.summary == ""

    def test_saving_a_published_version_with_a_changed_summary_is_refused(
        self, published_version
    ):
        published_version.summary = "Written afterwards"

        with pytest.raises(PublishedVersionError):
            published_version.save()

        published_version.refresh_from_db()
        assert published_version.summary == ""

    def test_updating_a_published_summary_through_the_queryset_is_refused(
        self, published_version
    ):
        with pytest.raises(PublishedVersionError):
            Version.objects.filter(pk=published_version.pk).update(
                summary="Written afterwards"
            )

        published_version.refresh_from_db()
        assert published_version.summary == ""

    def test_bulk_updating_a_published_summary_is_refused(self, published_version):
        published_version.summary = "Written afterwards"

        # bulk_update() wraps its internal update() in transaction.atomic(
        # savepoint=False), so the test supplies the savepoint.
        with pytest.raises(PublishedVersionError), transaction.atomic():
            Version.objects.bulk_update([published_version], ["summary"])

        published_version.refresh_from_db()
        assert published_version.summary == ""


@pytest.mark.django_db
class TestVersion:
    def test_a_draft_has_no_number(self, document):
        draft = Version.objects.create(document=document, markdown="Wording")

        assert draft.number is None
        assert str(draft) == f"{document} (draft)"

    def test_publishing_numbers_a_version_by_its_year_and_place_in_that_year(
        self, document
    ):
        year = timezone.localdate().year
        first = VersionFactory(document=document)
        first.publish()
        second = VersionFactory(document=document)
        second.publish()

        assert [first.number, second.number] == [f"{year}.1", f"{year}.2"]
        assert str(second) == f"{document} #{year}.2"

    def test_drafts_consume_no_numbers(self, document):
        year = timezone.localdate().year
        VersionFactory(document=document).publish()
        VersionFactory(document=document)
        VersionFactory(document=document)
        published_later = VersionFactory(document=document)

        published_later.publish()

        assert published_later.number == f"{year}.2"
        assert [v.number for v in document.versions.published()] == [
            f"{year}.1",
            f"{year}.2",
        ]
        assert [v.number for v in document.versions.drafts()] == [None, None]

    def test_the_count_starts_again_each_year(self, document, monkeypatch):
        this_year = timezone.now()
        next_year = this_year.replace(year=this_year.year + 1)
        VersionFactory(document=document).publish()
        VersionFactory(document=document).publish()
        monkeypatch.setattr(timezone, "now", lambda: next_year)

        version = VersionFactory(document=document)
        version.publish()

        assert version.number == f"{timezone.localdate(next_year).year}.1"

    @override_settings(TIME_ZONE="Europe/Berlin")
    def test_the_year_is_the_sites_local_year_at_publication(
        self, document, monkeypatch
    ):
        moment = datetime(2026, 12, 31, 23, 30, tzinfo=UTC)
        monkeypatch.setattr(timezone, "now", lambda: moment)

        version = VersionFactory(document=document)
        version.publish()

        assert version.number == "2027.1"

    @override_settings(USE_TZ=False)
    def test_a_site_without_time_zones_numbers_by_its_own_clock(
        self, document, monkeypatch
    ):
        moment = datetime(2031, 6, 1, 12, 0)
        monkeypatch.setattr(timezone, "now", lambda: moment)

        version = VersionFactory(document=document)
        version.publish()

        assert version.number == "2031.1"

    def test_numbers_are_counted_per_document(self):
        year = timezone.localdate().year
        privacy, terms = DocumentFactory(), DocumentFactory()
        VersionFactory(document=privacy).publish()
        VersionFactory(document=privacy).publish()

        terms_v1 = VersionFactory(document=terms)
        terms_v1.publish()

        assert terms_v1.number == f"{year}.1"

    def test_versions_are_ordered_by_publication_with_drafts_last(self, document):
        draft = VersionFactory(document=document)
        first = VersionFactory(document=document)
        first.publish()
        second = VersionFactory(document=document)
        second.publish()

        assert list(document.versions.all()) == [first, second, draft]

    def test_number_cannot_collide_within_a_document(self, published_version):
        with pytest.raises(IntegrityError):
            Version.objects.bulk_create(
                [
                    Version(
                        document=published_version.document,
                        markdown="Other wording",
                        number=published_version.number,
                        status=Version.Status.SUPERSEDED,
                        html="<p>Other wording</p>",
                        published_at=timezone.now(),
                    )
                ]
            )

    def test_a_draft_cannot_carry_a_number(self, document):
        with pytest.raises(IntegrityError):
            Version.objects.bulk_create(
                [Version(document=document, markdown="Wording", number="2026.1")]
            )

    def test_a_published_version_cannot_lack_a_number(self, document):
        with pytest.raises(IntegrityError):
            Version.objects.bulk_create(
                [
                    Version(
                        document=document,
                        markdown="Wording",
                        status=Version.Status.CURRENT,
                        html="<p>Wording</p>",
                        published_at=timezone.now(),
                    )
                ]
            )


@pytest.mark.django_db
class TestPublishing:
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
        # Two objects loaded from one draft is what a second process looks like from
        # here.
        draft = VersionFactory(document=document)
        first = Version.objects.get(pk=draft.pk)
        stale = Version.objects.get(pk=draft.pk)
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
        # An unfetched Version(pk=...) reports itself as being added, yet the write
        # lands as an update.
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
        # Asserted on the class: an already-written migration keeps a recorded manager
        # after the declaration goes.
        assert VersionManager.use_in_migrations is True

    def test_historical_version_model_uses_this_packages_manager(self):
        loader = MigrationLoader(connection)
        (leaf,) = loader.graph.leaf_nodes(app="mvp_compliance")
        state = loader.project_state(leaf)
        historical_version = state.apps.get_model("mvp_compliance", "Version")

        assert isinstance(historical_version.objects, VersionManager)


@pytest.mark.django_db
class TestRetrieval:
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
        year = timezone.localdate().year
        VersionFactory(document=document, markdown="First wording").publish()
        second = VersionFactory(document=document, markdown="Second wording")
        second.publish()
        VersionFactory(document=document, markdown="Third wording").publish()

        assert document.versions.get(number=f"{year}.2") == second

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

        year = timezone.localdate().year
        assert [v.number for v in privacy.versions.all()] == [f"{year}.1", f"{year}.2"]
        assert privacy.current == privacy_v2
        assert list(privacy.versions.published()) == [privacy_v1, privacy_v2]

        assert [v.number for v in terms.versions.all()] == [f"{year}.1"]
        assert terms.current == terms_v1
        assert list(terms.versions.published()) == [terms_v1]

        assert [v.number for v in cookies.versions.all()] == [None]
        assert cookies.current is None
        assert list(cookies.versions.published()) == []

        assert [v.number for v in agreement.versions.all()] == [
            f"{year}.1",
            f"{year}.2",
            f"{year}.3",
        ]
        assert agreement.current == agreement_v3
        assert list(agreement.versions.published()) == [
            agreement_v1,
            agreement_v2,
            agreement_v3,
        ]


@pytest.mark.django_db
class TestPublishingRefusesADuplicateOfTheVersionInForce:
    def test_publishing_a_duplicate_of_the_version_in_force_is_refused(self, document):
        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()
        duplicate = VersionFactory(document=document, markdown="The current wording")

        with pytest.raises(PublishError):
            duplicate.publish()

        duplicate.refresh_from_db()
        current.refresh_from_db()
        assert duplicate.status == Version.Status.DRAFT
        assert current.status == Version.Status.CURRENT

    def test_a_duplicate_differing_only_in_line_endings_is_refused(self, document):
        current = VersionFactory(
            document=document, markdown="## Heading\n\nA clause.\n"
        )
        current.publish()
        duplicate = VersionFactory(
            document=document, markdown="## Heading\r\n\r\nA clause."
        )

        with pytest.raises(PublishError):
            duplicate.publish()

        duplicate.refresh_from_db()
        assert duplicate.status == Version.Status.DRAFT

    def test_a_changed_wording_publishes(self, document):
        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()
        revised = VersionFactory(
            document=document, markdown="The current wording, revised"
        )

        revised.publish()

        revised.refresh_from_db()
        assert revised.status == Version.Status.CURRENT

    def test_a_documents_first_version_is_never_refused(self, document):
        first = VersionFactory(document=document, markdown="First wording")

        first.publish()

        first.refresh_from_db()
        assert first.status == Version.Status.CURRENT

    def test_a_duplicate_of_a_superseded_version_publishes(self, document):
        first = VersionFactory(document=document, markdown="The original wording")
        first.publish()
        second = VersionFactory(document=document, markdown="A rewording")
        second.publish()
        restoration = VersionFactory(document=document, markdown="The original wording")

        restoration.publish()

        restoration.refresh_from_db()
        assert restoration.status == Version.Status.CURRENT

    def test_a_draft_duplicating_the_current_wording_still_saves(self, document):
        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()

        duplicate = VersionFactory(document=document, markdown="The current wording")

        assert duplicate.pk is not None
        assert duplicate.status == Version.Status.DRAFT


@pytest.mark.django_db
class TestAcceptance:
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

    def test_recording_against_a_notice_is_refused_whether_or_not_it_is_in_force(
        self, user
    ):
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        superseded = VersionFactory(document=notice)
        superseded.publish()
        current = VersionFactory(document=notice)
        current.publish()
        superseded.refresh_from_db()

        for version in (current, superseded):
            with pytest.raises(RecordError):
                Acceptance.objects.record(user, version)

        assert not Acceptance.objects.exists()

    def test_recording_against_a_notice_is_refused_every_time(self, user):
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        version = VersionFactory(document=notice)
        version.publish()

        with pytest.raises(RecordError):
            Acceptance.objects.record(user, version)
        with pytest.raises(RecordError):
            Acceptance.objects.record(user, version)

        assert not Acceptance.objects.exists()

    def test_recording_against_a_document_made_a_notice_since_is_refused_and_the_old_record_stays(
        self, user, published_version
    ):
        old = Acceptance.objects.record(user, published_version)
        Document.objects.filter(pk=published_version.document_id).update(
            kind=Document.Kind.NOTICE
        )

        with pytest.raises(RecordError):
            Acceptance.objects.record(user, published_version)

        assert list(Acceptance.objects.all()) == [old]
        stored = Acceptance.objects.get()
        assert stored.accepted_at == old.accepted_at

    def test_a_document_instance_loaded_before_it_became_a_notice_lets_nothing_through(
        self, user
    ):
        version = VersionFactory()
        version.publish()
        assert version.document.kind == Document.Kind.AGREED
        Document.objects.filter(pk=version.document_id).update(
            kind=Document.Kind.NOTICE
        )

        with pytest.raises(RecordError):
            Acceptance.objects.record(user, version)

        assert not Acceptance.objects.exists()

    def test_creating_an_acceptance_of_a_notice_is_refused(self, user):
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        version = VersionFactory(document=notice)
        version.publish()

        with pytest.raises(RecordError):
            Acceptance.objects.create(
                user=user,
                subject=Acceptance.subject_of(user),
                version=version,
                accepted_at=timezone.now(),
            )
        with pytest.raises(RecordError):
            AcceptanceFactory(user=user, version=version)

        assert not Acceptance.objects.exists()

    def test_bulk_creating_with_one_notice_in_the_batch_writes_none_of_it(self, user):
        agreed = VersionFactory()
        agreed.publish()
        notice = VersionFactory(document=DocumentFactory(kind=Document.Kind.NOTICE))
        notice.publish()
        other = UserFactory()

        with pytest.raises(RecordError):
            Acceptance.objects.bulk_create(
                [
                    Acceptance(
                        user=person,
                        subject=Acceptance.subject_of(person),
                        version=version,
                        accepted_at=timezone.now(),
                    )
                    for person, version in [(user, agreed), (other, notice)]
                ]
            )

        assert not Acceptance.objects.exists()

    def test_bulk_creating_acceptances_of_agreed_documents_is_unaffected(self, user):
        version = VersionFactory()
        version.publish()

        Acceptance.objects.bulk_create(
            [
                Acceptance(
                    user=user,
                    subject=Acceptance.subject_of(user),
                    version=version,
                    accepted_at=timezone.now(),
                )
            ]
        )

        assert Acceptance.objects.count() == 1

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
        alice = UserFactory()
        bob = UserFactory()

        alice_acceptance = Acceptance.objects.record(alice, published_version)
        bob_acceptance = Acceptance.objects.record(bob, published_version)

        assert alice_acceptance.subject != bob_acceptance.subject
        assert Acceptance.objects.filter(version=published_version).count() == 2

    def test_the_same_version_twice_leaves_one_record(self, user, published_version):
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
        # The first lookup misses and commits a competing row as a side effect, so
        # record()'s own create() collides as two concurrent calls would.
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
class TestRecordMany:
    @staticmethod
    def published_versions(count):
        """Publish ``count`` versions, each of a document of its own."""
        versions = []
        for _ in range(count):
            version = VersionFactory()
            version.publish()
            versions.append(version)
        return versions

    def test_writes_one_acceptance_per_version_for_the_user(self, user):
        versions = self.published_versions(3)
        before = timezone.now()

        Acceptance.objects.record_many(user, versions)

        after = timezone.now()
        written = Acceptance.objects.for_person(user)
        assert {acceptance.version_id for acceptance in written} == {
            version.pk for version in versions
        }
        for acceptance in written:
            assert acceptance.user == user
            assert acceptance.subject == Acceptance.subject_of(user)
            assert before <= acceptance.accepted_at <= after

    def test_a_version_already_accepted_is_passed_over_and_its_record_unchanged(
        self, user
    ):
        accepted, other = self.published_versions(2)
        original = Acceptance.objects.record(user, accepted)

        Acceptance.objects.record_many(user, [accepted, other])

        assert Acceptance.objects.for_person(user).count() == 2
        stored = Acceptance.objects.get(subject=original.subject, version=accepted)
        assert stored.pk == original.pk
        assert stored.accepted_at == original.accepted_at

    def test_a_draft_is_refused_and_nothing_in_the_batch_is_written(self, user, draft):
        (published_version,) = self.published_versions(1)

        with pytest.raises(RecordError):
            Acceptance.objects.record_many(user, [published_version, draft])

        assert not Acceptance.objects.exists()

    def test_a_notices_version_is_refused_and_nothing_in_the_batch_is_written(
        self, user
    ):
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        notice_version = VersionFactory(document=notice)
        notice_version.publish()
        (published_version,) = self.published_versions(1)

        with pytest.raises(RecordError):
            Acceptance.objects.record_many(user, [published_version, notice_version])

        assert not Acceptance.objects.exists()

    def test_the_address_is_held_when_the_setting_is_on(self, user):
        (version,) = self.published_versions(1)
        request = RequestFactory().post("/", REMOTE_ADDR="203.0.113.5")

        with override_settings(MVP_COMPLIANCE_RECORD_IP_ADDRESS=True):
            Acceptance.objects.record_many(user, [version], request=request)

        assert Acceptance.objects.get().ip_address == "203.0.113.5"

    def test_no_address_is_held_when_the_setting_is_off(self, user):
        (version,) = self.published_versions(1)
        request = RequestFactory().post("/", REMOTE_ADDR="203.0.113.5")

        Acceptance.objects.record_many(user, [version], request=request)

        assert Acceptance.objects.get().ip_address is None

    def test_a_user_that_was_never_saved_is_refused(self, published_version):
        unsaved = get_user_model()(username="not-saved")

        with pytest.raises(RecordError):
            Acceptance.objects.record_many(unsaved, [published_version])

        assert not Acceptance.objects.exists()

    def test_an_empty_batch_writes_nothing(self, user):
        Acceptance.objects.record_many(user, [])

        assert not Acceptance.objects.exists()

    def test_the_cost_does_not_grow_with_the_number_of_versions(self, user):
        (one,) = self.published_versions(1)
        five = self.published_versions(5)

        with CaptureQueriesContext(connection) as for_one:
            Acceptance.objects.record_many(user, [one])
        with CaptureQueriesContext(connection) as for_five:
            Acceptance.objects.record_many(user, five)

        assert len(for_one) == len(for_five)


@pytest.mark.django_db
class TestAcceptanceImmutability:
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

    def test_an_update_matching_nothing_is_refused_too(self, published_version):
        # A check-then-write guard would let this through, and write to a record
        # committed in between.
        with pytest.raises(RecordedAcceptanceError):
            Acceptance.objects.filter(subject="nobody").update(subject="tampered")

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
        loader = MigrationLoader(connection)
        (leaf,) = loader.graph.leaf_nodes(app="mvp_compliance")
        state = loader.project_state(leaf)
        historical_acceptance = state.apps.get_model("mvp_compliance", "Acceptance")

        assert isinstance(historical_acceptance.objects, AcceptanceManager)


@pytest.mark.django_db
class TestOutstanding:
    def test_nothing_outstanding_once_the_version_in_force_is_accepted(
        self, user, published_version
    ):
        document = published_version.document
        Acceptance.objects.record(user, published_version)

        assert not document.is_outstanding_for(user)

    def test_outstanding_when_nothing_has_ever_been_accepted(
        self, user, published_version
    ):
        document = published_version.document

        assert document.is_outstanding_for(user)

    def test_outstanding_when_the_accepted_version_has_been_superseded(
        self, user, document
    ):
        first = VersionFactory(document=document)
        first.publish()
        Acceptance.objects.record(user, first)

        second = VersionFactory(document=document)
        second.publish()

        assert document.is_outstanding_for(user)

    def test_not_outstanding_when_nothing_has_ever_been_published(self, user, document):
        assert not document.is_outstanding_for(user)

    def test_outstanding_for_names_exactly_the_unaccepted_documents(self, user):
        accepted_document = DocumentFactory()
        accepted_version = VersionFactory(document=accepted_document)
        accepted_version.publish()
        Acceptance.objects.record(user, accepted_version)

        superseded_document = DocumentFactory()
        superseded_version = VersionFactory(document=superseded_document)
        superseded_version.publish()
        Acceptance.objects.record(user, superseded_version)
        VersionFactory(document=superseded_document).publish()

        never_accepted_document = DocumentFactory()
        VersionFactory(document=never_accepted_document).publish()

        DocumentFactory()  # never published — must not appear either way

        outstanding = Document.objects.outstanding_for(user)

        assert set(outstanding) == {superseded_document, never_accepted_document}

    def test_nothing_outstanding_is_an_empty_result_not_an_error(
        self, user, published_version
    ):
        Acceptance.objects.record(user, published_version)

        outstanding = Document.objects.outstanding_for(user)

        assert list(outstanding) == []

    def test_the_answer_costs_a_fixed_number_of_queries(
        self, user, django_assert_num_queries
    ):
        for _ in range(2):
            VersionFactory().publish()

        with django_assert_num_queries(1) as at_two_documents:
            list(Document.objects.outstanding_for(user))

        for _ in range(8):  # ten documents total
            VersionFactory().publish()

        with django_assert_num_queries(1) as at_ten_documents:
            list(Document.objects.outstanding_for(user))

        assert len(at_two_documents.captured_queries) == len(
            at_ten_documents.captured_queries
        )

    def test_a_notice_with_a_version_in_force_is_not_outstanding(self, user):
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        VersionFactory(document=notice).publish()

        assert not notice.is_outstanding_for(user)
        assert notice not in Document.objects.outstanding_for(user)

    def test_a_document_created_without_a_kind_is_outstanding_until_accepted(
        self, user
    ):
        document = Document.objects.create(name="Terms", slug="terms")
        VersionFactory(document=document).publish()

        assert document.is_outstanding_for(user)

    def test_outstanding_for_names_the_agreed_documents_not_yet_accepted_among_notices(
        self, user
    ):
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        VersionFactory(document=notice).publish()
        unaccepted = DocumentFactory()
        VersionFactory(document=unaccepted).publish()
        accepted = DocumentFactory()
        accepted_version = VersionFactory(document=accepted)
        accepted_version.publish()
        Acceptance.objects.record(user, accepted_version)

        assert set(Document.objects.outstanding_for(user)) == {unaccepted}

    def test_a_notice_with_only_drafts_is_outstanding_for_nobody(self, user):
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        VersionFactory(document=notice)

        assert not notice.is_outstanding_for(user)

    def test_a_kind_that_is_not_a_notice_leaves_the_document_outstanding(self, user):
        document = DocumentFactory()
        VersionFactory(document=document).publish()
        Document.objects.filter(pk=document.pk).update(kind="something-else")

        assert document.is_outstanding_for(user)

    def test_the_answer_costs_the_same_with_one_document_as_with_fifty_with_notices(
        self, user, django_assert_num_queries
    ):
        VersionFactory(document=DocumentFactory(kind=Document.Kind.NOTICE)).publish()

        with django_assert_num_queries(1) as at_two_documents:
            list(Document.objects.outstanding_for(user))

        for n in range(49):
            kind = Document.Kind.NOTICE if n % 5 == 0 else Document.Kind.AGREED
            VersionFactory(document=DocumentFactory(kind=kind)).publish()

        with django_assert_num_queries(1) as at_fifty_documents:
            list(Document.objects.outstanding_for(user))

        assert len(at_two_documents.captured_queries) == len(
            at_fifty_documents.captured_queries
        )


@pytest.mark.django_db
class TestAccountRemoval:
    def test_acceptances_survive_by_default(self, user, published_version):
        acceptance = Acceptance.objects.record(user, published_version)
        subject = acceptance.subject

        user.delete()

        acceptance.refresh_from_db()
        assert acceptance.subject == subject
        assert acceptance.version == published_version
        assert acceptance.user_id is None

    def test_acceptances_removed_when_the_setting_says_so(
        self, user, published_version
    ):
        Acceptance.objects.record(user, published_version)
        subject = Acceptance.subject_of(user)

        with override_settings(
            MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL=False
        ):
            user.delete()

        assert not Acceptance.objects.filter(subject=subject).exists()

    def test_removing_one_account_does_not_touch_anyone_elses_records_by_default(
        self, published_version
    ):
        survivor = UserFactory()
        survivor_acceptance = Acceptance.objects.record(survivor, published_version)
        removed = UserFactory()
        Acceptance.objects.record(removed, published_version)

        removed.delete()

        survivor_acceptance.refresh_from_db()
        assert survivor_acceptance.user_id == survivor.pk

    def test_removing_one_account_does_not_touch_anyone_elses_records_when_the_setting_says_so(
        self, published_version
    ):
        survivor = UserFactory()
        survivor_acceptance = Acceptance.objects.record(survivor, published_version)
        removed = UserFactory()
        Acceptance.objects.record(removed, published_version)

        with override_settings(
            MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL=False
        ):
            removed.delete()

        assert Acceptance.objects.filter(pk=survivor_acceptance.pk).exists()

    def test_a_surviving_record_is_still_found_with_its_siblings(
        self, user, document, monkeypatch
    ):
        earlier_version = VersionFactory(document=document)
        earlier_version.publish()
        later_version = VersionFactory(document=document)
        later_version.publish()

        later_moment = timezone.now()
        earlier_moment = later_moment - timedelta(minutes=5)

        monkeypatch.setattr(timezone, "now", lambda: earlier_moment)
        earlier = Acceptance.objects.record(user, earlier_version)

        monkeypatch.setattr(timezone, "now", lambda: later_moment)
        later = Acceptance.objects.record(user, later_version)

        subject = earlier.subject
        user.delete()

        assert list(Acceptance.objects.for_subject(subject)) == [earlier, later]

    def test_a_recreated_account_inherits_nothing(self, published_version):
        original = UserFactory(username="alex")
        Acceptance.objects.record(original, published_version)
        original.delete()

        recreated = UserFactory(username="alex")

        assert list(Acceptance.objects.for_person(recreated)) == []

    def test_the_collector_does_not_update_through_the_guarded_queryset(self):
        # lazy_sub_objs on the on_delete callable plus base_manager_name together would
        # route account removal into the refusing queryset.
        assert not hasattr(keep_or_remove_acceptances, "lazy_sub_objs")
        assert Acceptance._meta.base_manager_name is None
        assert not isinstance(Acceptance._base_manager.all(), AcceptanceQuerySet)


@pytest.mark.django_db
class TestOptionalEvidence:
    def test_holds_nothing_beyond_the_three_facts_by_default(
        self, user, published_version
    ):
        acceptance = Acceptance.objects.record(user, published_version)

        assert acceptance.ip_address is None

    def test_a_request_under_the_defaults_still_holds_no_address(
        self, user, published_version
    ):
        # A request is supplied: without one this would pass even if the address were
        # read unconditionally.
        request = RequestFactory().post("/", REMOTE_ADDR="203.0.113.5")

        acceptance = Acceptance.objects.record(user, published_version, request)

        assert acceptance.ip_address is None

    def test_holds_the_address_when_the_setting_is_on_and_a_request_is_supplied(
        self, user, published_version
    ):
        request = RequestFactory().post("/", REMOTE_ADDR="203.0.113.5")

        with override_settings(MVP_COMPLIANCE_RECORD_IP_ADDRESS=True):
            acceptance = Acceptance.objects.record(
                user, published_version, request=request
            )

        assert acceptance.ip_address == "203.0.113.5"

    def test_a_forwarded_header_is_never_read_even_when_it_disagrees(
        self, user, published_version
    ):
        # A forwarded header is set by the client, so reading one would let a person
        # write their own evidence (docs/adr/0010).
        request = RequestFactory().post(
            "/",
            REMOTE_ADDR="203.0.113.5",
            HTTP_X_FORWARDED_FOR="198.51.100.9",
            HTTP_X_REAL_IP="198.51.100.9",
            HTTP_FORWARDED="for=198.51.100.9",
        )

        with override_settings(MVP_COMPLIANCE_RECORD_IP_ADDRESS=True):
            acceptance = Acceptance.objects.record(
                user, published_version, request=request
            )

        assert acceptance.ip_address == "203.0.113.5"

    def test_a_record_made_before_the_setting_was_on_is_unchanged_afterwards(
        self, user, published_version
    ):
        acceptance = Acceptance.objects.record(user, published_version)

        with override_settings(MVP_COMPLIANCE_RECORD_IP_ADDRESS=True):
            acceptance.refresh_from_db()

        assert acceptance.ip_address is None

    def test_a_record_made_while_the_setting_was_on_still_holds_it_once_turned_off(
        self, user, published_version
    ):
        request = RequestFactory().post("/", REMOTE_ADDR="203.0.113.5")

        with override_settings(MVP_COMPLIANCE_RECORD_IP_ADDRESS=True):
            acceptance = Acceptance.objects.record(
                user, published_version, request=request
            )

        acceptance.refresh_from_db()
        assert acceptance.ip_address == "203.0.113.5"

    def test_no_request_holds_no_address(self, user, published_version):
        with override_settings(MVP_COMPLIANCE_RECORD_IP_ADDRESS=True):
            acceptance = Acceptance.objects.record(user, published_version)

        assert acceptance.ip_address is None


class TestPublisher:
    def test_an_unsaved_publisher_is_refused_before_anything_changes(self, draft):
        with pytest.raises(RecordError):
            draft.publish(publisher=get_user_model()(username="unsaved"))

        assert draft.status == draft.Status.DRAFT
        assert draft.published_at is None
        assert draft.publisher is None
        draft.refresh_from_db()
        assert draft.status == draft.Status.DRAFT

    def test_publishing_records_the_publisher_and_their_subject(self, draft, user):
        draft.publish(publisher=user)

        draft.refresh_from_db()
        assert draft.publisher == user
        assert draft.publisher_subject == Acceptance.subject_of(user)

    def test_publishing_with_nobody_named_leaves_both_empty(self, draft):
        draft.publish()

        draft.refresh_from_db()
        assert draft.publisher is None
        assert draft.publisher_subject == ""

    def test_a_draft_has_no_publisher(self, draft):
        assert draft.publisher is None
        assert draft.publisher_subject == ""

    def test_publishing_as_an_unsaved_user_is_refused_and_leaves_the_draft_alone(
        self, draft
    ):
        with pytest.raises(RecordError):
            draft.publish(publisher=get_user_model()(username="nobody"))

        draft.refresh_from_db()
        assert draft.status == Version.Status.DRAFT

    def test_the_database_refuses_a_draft_that_names_a_publisher(self, user):
        document = DocumentFactory()

        with pytest.raises(IntegrityError), transaction.atomic():
            Version.objects.create(
                document=document, markdown="Wording", publisher=user
            )

        with pytest.raises(IntegrityError), transaction.atomic():
            Version.objects.create(
                document=document, markdown="Wording", publisher_subject="7"
            )

    def test_saving_a_published_version_with_a_changed_publisher_is_refused(
        self, draft, user
    ):
        draft.publish(publisher=user)
        draft.publisher = UserFactory()

        with pytest.raises(PublishedVersionError):
            draft.save()

        draft.refresh_from_db()
        assert draft.publisher == user

    def test_saving_a_published_version_with_a_changed_publisher_subject_is_refused(
        self, draft, user
    ):
        draft.publish(publisher=user)
        draft.publisher_subject = "someone-else"

        with pytest.raises(PublishedVersionError):
            draft.save()

        draft.refresh_from_db()
        assert draft.publisher_subject == Acceptance.subject_of(user)

    @pytest.mark.parametrize(
        "field", ["publisher", "publisher_id", "publisher_subject"]
    )
    def test_updating_the_publisher_through_the_queryset_is_refused(
        self, draft, user, field
    ):
        draft.publish(publisher=user)
        other = UserFactory()
        value = "someone-else" if field == "publisher_subject" else other.pk
        if field == "publisher":
            value = other

        with pytest.raises(PublishedVersionError):
            Version.objects.filter(pk=draft.pk).update(**{field: value})

        draft.refresh_from_db()
        assert draft.publisher == user
        assert draft.publisher_subject == Acceptance.subject_of(user)

    def test_removing_the_publishers_account_succeeds_and_keeps_only_the_subject(
        self, draft, user
    ):
        draft.publish(publisher=user)
        draft.refresh_from_db()
        subject = draft.publisher_subject
        before = {
            name: getattr(draft, name)
            for name in ("document_id", "number", "markdown", "html", "published_at")
        }

        user.delete()

        draft.refresh_from_db()
        assert draft.publisher is None
        assert draft.publisher_subject == subject
        assert draft.status == Version.Status.CURRENT
        assert {name: getattr(draft, name) for name in before} == before

    def test_removing_an_account_that_published_nothing_touches_no_version(
        self, published_version
    ):
        other = UserFactory()

        other.delete()

        published_version.refresh_from_db()
        assert published_version.status == Version.Status.CURRENT


class TestPublisherDisplay:
    def test_a_draft_says_nothing(self, draft):
        assert draft.publisher_display is None

    def test_a_version_published_by_an_existing_account_names_it(self, draft, user):
        draft.publish(publisher=user)

        assert draft.publisher_display == str(user)

    def test_a_version_whose_publisher_was_removed_says_so_without_the_subject(
        self, draft, user
    ):
        draft.publish(publisher=user)
        subject = draft.publisher_subject
        user.delete()
        draft.refresh_from_db()
        nobody_named = VersionFactory()
        nobody_named.publish()

        assert draft.publisher_display
        assert subject not in draft.publisher_display
        assert draft.publisher_display != nobody_named.publisher_display

    def test_a_version_published_with_nobody_named_says_so(self, draft, user):
        named = VersionFactory()
        named.publish(publisher=user)
        draft.publish()

        assert draft.publisher_display
        assert draft.publisher_display != named.publisher_display

    def test_a_version_published_before_publishers_were_kept_says_so(
        self, published_version
    ):
        nobody_named = VersionFactory()
        nobody_named.publish()

        assert published_version.publisher_id is None
        assert published_version.publisher_subject == ""
        assert published_version.publisher_display == nobody_named.publisher_display


class TestVersionPublished:
    def test_a_receiver_runs_once_with_the_version_publisher_and_replaced(
        self, announcements, django_capture_on_commit_callbacks, draft, user
    ):
        with django_capture_on_commit_callbacks(execute=True):
            draft.publish(publisher=user)

        assert len(announcements) == 1
        call = announcements[0]
        assert call["sender"] is Version
        assert call["version"] == draft
        assert call["publisher"] == user
        assert call["replaced"] is None

    def test_publishing_a_notices_version_is_announced_too(
        self, announcements, django_capture_on_commit_callbacks, db
    ):
        version = VersionFactory(document=DocumentFactory(kind=Document.Kind.NOTICE))

        with django_capture_on_commit_callbacks(execute=True):
            version.publish()

        assert [call["version"] for call in announcements] == [version]

    def test_a_publication_with_nobody_named_passes_none_as_publisher(
        self, announcements, django_capture_on_commit_callbacks, draft
    ):
        with django_capture_on_commit_callbacks(execute=True):
            draft.publish()

        assert announcements[0]["publisher"] is None

    def test_replaced_is_the_superseded_version_already_marked_superseded(
        self, announcements, django_capture_on_commit_callbacks, published_version
    ):
        second = VersionFactory(
            document=published_version.document, markdown="Different wording."
        )

        with django_capture_on_commit_callbacks(execute=True):
            second.publish()

        assert len(announcements) == 1
        replaced = announcements[0]["replaced"]
        assert replaced == published_version
        assert replaced.status == Version.Status.SUPERSEDED

    def test_none_of_the_three_refusals_announces_anything(
        self, announcements, django_capture_on_commit_callbacks, published_version
    ):
        document = published_version.document
        same_wording = VersionFactory(
            document=document, markdown=published_version.markdown
        )
        empty = VersionFactory(document=DocumentFactory(), markdown="   \n\n   ")
        control = VersionFactory(document=DocumentFactory())

        with django_capture_on_commit_callbacks(execute=True):
            with pytest.raises(PublishError):
                published_version.publish()
            with pytest.raises(PublishError):
                empty.publish()
            with pytest.raises(PublishError):
                same_wording.publish()
        assert announcements == []

        with django_capture_on_commit_callbacks(execute=True):
            control.publish()
        assert [call["version"] for call in announcements] == [control]

    def test_a_publication_inside_a_rolled_back_block_announces_nothing(
        self, announcements, django_capture_on_commit_callbacks, draft
    ):
        control = VersionFactory()

        with (
            django_capture_on_commit_callbacks(execute=True),
            pytest.raises(RuntimeError),
            transaction.atomic(),
        ):
            draft.publish()
            raise RuntimeError("roll back")
        assert announcements == []

        with django_capture_on_commit_callbacks(execute=True):
            control.publish()
        assert [call["version"] for call in announcements] == [control]

    def test_the_receiver_sees_the_version_current_and_the_old_one_superseded(
        self, connect, django_capture_on_commit_callbacks, published_version
    ):
        second = VersionFactory(
            document=published_version.document, markdown="Different wording."
        )
        seen = []

        def look(sender, version, replaced, **kwargs):
            seen.append(
                (
                    Version.objects.get(pk=version.pk).status,
                    Version.objects.get(pk=replaced.pk).status,
                )
            )

        connect(look)

        with django_capture_on_commit_callbacks(execute=True):
            second.publish()

        assert seen == [(Version.Status.CURRENT, Version.Status.SUPERSEDED)]

    def test_nothing_is_announced_until_the_outer_transaction_commits(
        self, announcements, django_capture_on_commit_callbacks, draft
    ):
        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            draft.publish()

        assert announcements == []
        assert len(callbacks) == 1

    def test_a_raising_receiver_cannot_undo_or_hide_the_publication(
        self, connect, django_capture_on_commit_callbacks, caplog, draft
    ):
        later = []

        def fail(sender, **kwargs):
            raise ValueError("receiver broke")

        connect(fail)
        connect(lambda sender, **kwargs: later.append(kwargs["version"]))

        with (
            caplog.at_level("ERROR", logger="django.dispatch"),
            django_capture_on_commit_callbacks(execute=True),
        ):
            draft.publish()

        draft.refresh_from_db()
        assert draft.status == Version.Status.CURRENT
        assert later == [draft]
        errors = [r for r in caplog.records if r.name == "django.dispatch"]
        assert len(errors) == 1
        assert errors[0].levelname == "ERROR"
        assert errors[0].exc_info is not None

    def test_a_receiver_that_publishes_another_version_announces_that_one_too(
        self, announcements, connect, django_capture_on_commit_callbacks, draft
    ):
        follow_up = VersionFactory()

        def publish_another(sender, version, **kwargs):
            if version == draft:
                follow_up.publish()

        connect(publish_another)

        with django_capture_on_commit_callbacks(execute=True):
            draft.publish()

        assert [call["version"] for call in announcements] == [draft, follow_up]

    def test_two_documents_published_in_one_transaction_are_each_announced_once(
        self, db, announcements, django_capture_on_commit_callbacks
    ):
        first, second = VersionFactory(), VersionFactory()

        with django_capture_on_commit_callbacks(execute=True), transaction.atomic():
            first.publish()
            second.publish()
            assert announcements == []

        assert [call["version"] for call in announcements] == [first, second]


def change_kind(document, kind, route):
    """Change ``document``'s kind through ``save()`` or through ``update()``."""
    if route == "save":
        document.kind = kind
        document.save()
    else:
        Document.objects.filter(pk=document.pk).update(kind=kind)
    document.refresh_from_db()


def held_about(document):
    """Every version and acceptance of ``document`` as plain rows, to compare before and after."""
    versions = document.versions.order_by("pk").values_list(
        "pk", "number", "status", "markdown", "html", "published_at"
    )
    acceptances = Acceptance.objects.filter(version__document=document).order_by("pk")
    return list(versions), list(
        acceptances.values_list(
            "pk", "subject", "version_id", "accepted_at", "ip_address"
        )
    )


@pytest.mark.django_db
class TestChangingTheKind:
    """US-2 scenarios 3-6, FR-007, FR-008, SC-003: the kind changes and nothing recorded does."""

    @pytest.fixture
    def agreed_document(self, user):
        """A document people agree to, with two published versions, each accepted by ``user``."""
        document = DocumentFactory()
        for wording in ("First wording", "Second wording"):
            version = VersionFactory(document=document, markdown=wording)
            version.publish()
            Acceptance.objects.record(user, version)
        return document

    @pytest.mark.parametrize("route", ["save", "update"])
    def test_making_a_document_a_notice_leaves_its_versions_and_acceptances_as_they_were(
        self, agreed_document, route
    ):
        before = held_about(agreed_document)

        change_kind(agreed_document, Document.Kind.NOTICE, route)

        assert agreed_document.kind == Document.Kind.NOTICE
        assert held_about(agreed_document) == before
        assert len(before[0]) == 2
        assert len(before[1]) == 2

    @pytest.mark.parametrize("route", ["save", "update"])
    def test_making_a_notice_a_document_people_agree_to_leaves_its_versions_and_acceptances_as_they_were(
        self, agreed_document, route
    ):
        change_kind(agreed_document, Document.Kind.NOTICE, "update")
        before = held_about(agreed_document)

        change_kind(agreed_document, Document.Kind.AGREED, route)

        assert agreed_document.kind == Document.Kind.AGREED
        assert held_about(agreed_document) == before
        assert len(before[0]) == 2
        assert len(before[1]) == 2

    @pytest.mark.parametrize("route", ["save", "update"])
    def test_acceptances_of_a_document_made_a_notice_still_appear_in_the_persons_record(
        self, agreed_document, user, route
    ):
        change_kind(agreed_document, Document.Kind.NOTICE, route)

        entries = produce(Acceptance.subject_of(user)).sections[0].entries

        assert [entry.document for entry in entries] == [agreed_document.name] * 2
        assert {entry.version for entry in entries} == {
            version.number for version in agreed_document.versions.all()
        }

    @pytest.mark.parametrize("route", ["save", "update"])
    def test_a_document_made_a_notice_is_not_outstanding_for_someone_who_never_accepted_it(
        self, agreed_document, route
    ):
        stranger = UserFactory()
        assert agreed_document.is_outstanding_for(stranger)

        change_kind(agreed_document, Document.Kind.NOTICE, route)

        assert not agreed_document.is_outstanding_for(stranger)
        assert agreed_document not in Document.objects.outstanding_for(stranger)

    @pytest.mark.parametrize("route", ["save", "update"])
    def test_a_notice_made_a_document_people_agree_to_is_outstanding_for_someone_who_has_not_accepted_it(
        self, route
    ):
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        VersionFactory(document=notice).publish()
        person = UserFactory()
        assert not notice.is_outstanding_for(person)

        change_kind(notice, Document.Kind.AGREED, route)

        assert notice.is_outstanding_for(person)
        assert notice in Document.objects.outstanding_for(person)

    @pytest.mark.parametrize("route", ["save", "update"])
    def test_an_acceptance_from_before_it_was_a_notice_counts_again_once_it_is_agreed_to_again(
        self, agreed_document, user, route
    ):
        change_kind(agreed_document, Document.Kind.NOTICE, route)

        change_kind(agreed_document, Document.Kind.AGREED, route)

        assert not agreed_document.is_outstanding_for(user)
        assert agreed_document not in Document.objects.outstanding_for(user)


@pytest.mark.django_db
class TestAcceptancesOfAgreedDocuments:
    """US-1 scenarios 2 and 8, edge cases 1 and 2, FR-002, SC-001: the page's records."""

    def accept_published(self, user, document):
        """Publish a new version of ``document``, accept it as ``user`` and return the acceptance."""
        wording = f"Wording {document.versions.count() + 1}"
        version = VersionFactory(document=document, markdown=wording)
        version.publish()
        return Acceptance.objects.record(user, version)

    def test_holds_exactly_the_persons_own_acceptances_of_documents_people_agree_to(
        self, user
    ):
        agreed = DocumentFactory()
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        mine = self.accept_published(user, agreed)
        self.accept_published(UserFactory(), agreed)
        VersionFactory(document=notice).publish()

        result = list(Acceptance.objects.for_person(user).of_agreed_documents())

        assert result == [mine]

    def test_is_ordered_by_document_name_then_newest_published_first(self, user):
        beta = DocumentFactory(name="Beta terms")
        alpha = DocumentFactory(name="Alpha terms")
        beta_first = self.accept_published(user, beta)
        alpha_first = self.accept_published(user, alpha)
        beta_second = self.accept_published(user, beta)
        alpha_second = self.accept_published(user, alpha)

        result = list(Acceptance.objects.for_person(user).of_agreed_documents())

        assert result == [alpha_second, alpha_first, beta_second, beta_first]

    def test_leaves_out_a_version_the_person_never_accepted_between_two_they_did(
        self, user
    ):
        document = DocumentFactory()
        first = self.accept_published(user, document)
        skipped = VersionFactory(document=document)
        skipped.publish()
        third = self.accept_published(user, document)

        result = Acceptance.objects.for_person(user).of_agreed_documents()

        assert [acceptance.version for acceptance in result] == [
            third.version,
            first.version,
        ]
        assert skipped not in [acceptance.version for acceptance in result]

    @pytest.mark.parametrize("route", ["save", "update"])
    def test_drops_a_document_made_a_notice_and_brings_it_back_when_agreed_to_again(
        self, user, route
    ):
        document = DocumentFactory()
        acceptance = self.accept_published(user, document)

        change_kind(document, Document.Kind.NOTICE, route)
        while_a_notice = list(Acceptance.objects.for_person(user).of_agreed_documents())
        change_kind(document, Document.Kind.AGREED, route)
        once_agreed_again = list(
            Acceptance.objects.for_person(user).of_agreed_documents()
        )

        assert while_a_notice == []
        assert once_agreed_again == [acceptance]

    def test_reads_in_one_query_with_the_version_and_document_loaded(
        self, user, django_assert_num_queries
    ):
        for _ in range(3):
            self.accept_published(user, DocumentFactory())

        with django_assert_num_queries(1):
            result = list(Acceptance.objects.for_person(user).of_agreed_documents())
            names = [acceptance.version.document.name for acceptance in result]

        assert len(names) == 3


def change_enforced(document, enforced, route):
    """Change ``document``'s enforcement through ``save()`` or through ``update()``.

    Returns:
        The value as stored afterwards, read back from the database.
    """
    if route == "save":
        document.enforced = enforced
        document.save()
    else:
        Document.objects.filter(pk=document.pk).update(enforced=enforced)
    return Document.objects.values_list("enforced", flat=True).get(pk=document.pk)


@pytest.mark.django_db
class TestEnforcement:
    """US-2 scenarios 2, 4, 6, 8-10, FR-010 to FR-013, FR-015, SC-006."""

    def test_a_document_created_with_no_choice_made_is_enforced(self):
        document = Document.objects.create(name="Terms", slug="terms")

        document.refresh_from_db()

        assert document.enforced

    def test_returns_an_enforced_document_whose_version_in_force_is_unaccepted(
        self, user
    ):
        document = DocumentFactory()
        VersionFactory(document=document).publish()

        assert set(Document.objects.enforced_outstanding_for(user)) == {document}

    def test_leaves_out_a_document_that_is_not_enforced(self, user):
        document = DocumentFactory(enforced=False)
        VersionFactory(document=document).publish()

        assert document not in Document.objects.enforced_outstanding_for(user)

    def test_leaves_out_a_notice_marked_enforced(self, user):
        notice = DocumentFactory(kind=Document.Kind.NOTICE, enforced=True)
        VersionFactory(document=notice).publish()

        assert notice not in Document.objects.enforced_outstanding_for(user)

    def test_leaves_out_an_enforced_document_with_only_a_draft(self, user):
        document = DocumentFactory()
        VersionFactory(document=document)

        assert document not in Document.objects.enforced_outstanding_for(user)

    def test_leaves_out_an_enforced_document_whose_current_version_was_accepted(
        self, user
    ):
        document = DocumentFactory()
        version = VersionFactory(document=document)
        version.publish()
        Acceptance.objects.record(user, version)

        assert document not in Document.objects.enforced_outstanding_for(user)

    def test_returns_an_enforced_document_whose_accepted_version_was_superseded(
        self, user
    ):
        document = DocumentFactory()
        first = VersionFactory(document=document)
        first.publish()
        Acceptance.objects.record(user, first)
        VersionFactory(document=document).publish()

        assert set(Document.objects.enforced_outstanding_for(user)) == {document}

    def test_what_a_person_has_outstanding_still_counts_a_document_that_is_not_enforced(
        self, user
    ):
        document = DocumentFactory(enforced=False)
        VersionFactory(document=document).publish()

        assert document.is_outstanding_for(user)
        assert document in Document.objects.outstanding_for(user)

    @pytest.mark.parametrize("route", ["save", "update"])
    def test_switching_enforcement_off_and_on_leaves_versions_and_acceptances_as_they_were(
        self, user, route
    ):
        document = DocumentFactory()
        for wording in ("First wording", "Second wording"):
            version = VersionFactory(document=document, markdown=wording)
            version.publish()
            Acceptance.objects.record(user, version)
        before = held_about(document)

        stored_while_off = change_enforced(document, False, route)
        while_off = held_about(document)
        stored_once_on = change_enforced(document, True, route)

        assert stored_while_off is False
        assert stored_once_on is True
        assert while_off == before
        assert held_about(document) == before
        assert len(before[0]) == 2
        assert len(before[1]) == 2

    def test_the_answer_costs_the_same_with_one_document_as_with_ten(
        self, user, django_assert_num_queries
    ):
        VersionFactory().publish()

        with django_assert_num_queries(1) as at_one_document:
            list(Document.objects.enforced_outstanding_for(user))

        for _ in range(9):
            VersionFactory().publish()

        with django_assert_num_queries(1) as at_ten_documents:
            list(Document.objects.enforced_outstanding_for(user))

        assert len(at_one_document.captured_queries) == len(
            at_ten_documents.captured_queries
        )


@pytest.mark.django_db
class TestSkipAgreementPermission:
    """US-5 scenario 2, FR-019."""

    def test_the_permission_exists_after_migrating_with_document_as_its_content_type(
        self,
    ):
        permission = Permission.objects.get(
            content_type__app_label="mvp_compliance", codename="skip_agreement"
        )

        assert permission.content_type == ContentType.objects.get_for_model(Document)

    def test_a_user_holding_it_is_asked_for_it_by_the_name_the_middleware_uses(
        self, user
    ):
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Document),
                codename="skip_agreement",
            )
        )

        assert user.has_perm("mvp_compliance.skip_agreement")


def lock(version):
    """Lock a draft for translation, as the admin's lock page will."""
    version.lock_for_translation()
    return version


@pytest.mark.django_db
class TestPendingVersion:
    """A draft locked for translation: frozen wording, no standing (FS-015)."""

    def test_the_factory_builds_a_pending_version_with_no_standing(self):
        version = VersionFactory(pending=True)

        version.refresh_from_db()
        assert version.status == Version.Status.PENDING

    def test_locking_a_draft_makes_it_pending_with_no_standing(self, draft):
        draft.lock_for_translation()

        draft.refresh_from_db()
        assert draft.status == Version.Status.PENDING
        assert draft.number is None
        assert draft.published_at is None
        assert draft.html == ""
        assert draft.publisher is None
        assert draft.publisher_subject == ""

    def test_locking_renders_nothing(self, draft):
        draft.lock_for_translation()

        assert Version.objects.get(pk=draft.pk).html == ""

    def test_locking_consumes_no_number(self, document):
        first = VersionFactory(document=document)
        lock(first)
        second = VersionFactory(document=document, markdown="Second wording")

        second.publish()

        assert second.number.endswith(".1")

    @pytest.mark.parametrize("start", ["pending", "current", "superseded"])
    def test_locking_anything_but_a_draft_is_refused_and_writes_nothing(self, start):
        version = VersionFactory()
        if start == "pending":
            lock(version)
        else:
            version.publish()
            if start == "superseded":
                VersionFactory(document=version.document, markdown="Newer").publish()
        before = Version.objects.filter(pk=version.pk).values().get()

        with pytest.raises(PublishError):
            version.lock_for_translation()

        assert Version.objects.filter(pk=version.pk).values().get() == before

    def test_locking_a_draft_with_empty_output_is_refused(self, document):
        version = VersionFactory(document=document, markdown="   \n\n   ")

        with pytest.raises(PublishError):
            version.lock_for_translation()

        version.refresh_from_db()
        assert version.status == Version.Status.DRAFT

    def test_locking_a_draft_that_repeats_the_version_in_force_is_refused(
        self, published_version
    ):
        repeat = VersionFactory(
            document=published_version.document,
            markdown=f"{published_version.markdown}\r\n",
        )

        with pytest.raises(PublishError):
            repeat.lock_for_translation()

        repeat.refresh_from_db()
        assert repeat.status == Version.Status.DRAFT

    def test_locking_rechecks_the_stored_status_under_the_lock(self, draft):
        stale = Version.objects.get(pk=draft.pk)
        draft.publish()

        with pytest.raises(PublishError):
            stale.lock_for_translation()

        draft.refresh_from_db()
        assert draft.status == Version.Status.CURRENT

    def test_a_pending_wording_is_refused_a_change_through_save(self, draft):
        lock(draft)
        draft.markdown = "Changed"

        with pytest.raises(PublishedVersionError):
            draft.save()

        assert Version.objects.get(pk=draft.pk).markdown != "Changed"

    def test_a_pending_summary_is_refused_a_change_through_save(self, draft):
        lock(draft)
        draft.summary = "Changed"

        with pytest.raises(PublishedVersionError):
            draft.save()

        assert Version.objects.get(pk=draft.pk).summary == ""

    def test_a_pending_document_is_refused_a_change_through_save(self, draft):
        lock(draft)
        draft.document = DocumentFactory()

        with pytest.raises(PublishedVersionError):
            draft.save()

    @pytest.mark.parametrize("field", ["markdown", "summary"])
    def test_a_pending_wording_is_refused_a_change_through_update(self, draft, field):
        lock(draft)

        with pytest.raises(PublishedVersionError):
            Version.objects.filter(pk=draft.pk).update(**{field: "Changed"})

        assert getattr(Version.objects.get(pk=draft.pk), field) != "Changed"

    def test_a_pending_document_is_refused_a_change_through_update(self, draft):
        lock(draft)

        with pytest.raises(PublishedVersionError):
            Version.objects.filter(pk=draft.pk).update(document=DocumentFactory())

    def test_a_pending_wording_is_refused_a_change_through_bulk_update(self, draft):
        lock(draft)
        draft.markdown = "Changed"

        with pytest.raises(PublishedVersionError), transaction.atomic():
            Version.objects.bulk_update([draft], ["markdown"])

        assert Version.objects.get(pk=draft.pk).markdown != "Changed"

    def test_an_update_over_a_pending_row_and_a_draft_writes_neither(self, document):
        pending = lock(VersionFactory(document=document))
        draft = VersionFactory(document=document, markdown="Another draft")

        with pytest.raises(PublishedVersionError):
            Version.objects.filter(document=document).update(markdown="Changed")

        draft.refresh_from_db()
        assert draft.markdown == "Another draft"
        assert Version.objects.get(pk=pending.pk).markdown != "Changed"

    def test_a_draft_beside_a_pending_version_is_still_editable(self, document):
        lock(VersionFactory(document=document))
        draft = VersionFactory(document=document, markdown="Another draft")

        draft.markdown = "Revised"
        draft.save()

        assert Version.objects.get(pk=draft.pk).markdown == "Revised"

    def test_a_published_version_is_still_refused_every_frozen_field(
        self, published_version
    ):
        published_version.html = "<p>Other</p>"

        with pytest.raises(PublishedVersionError):
            published_version.save()

    def test_a_pending_version_saves_when_nothing_frozen_changed(self, draft):
        lock(draft)

        draft.save()

        assert Version.objects.get(pk=draft.pk).status == Version.Status.PENDING

    def test_a_pending_version_can_be_deleted(self, draft):
        lock(draft)
        pk = draft.pk

        draft.delete()

        assert not Version.objects.filter(pk=pk).exists()

    def test_a_pending_version_can_be_deleted_through_the_queryset(self, draft):
        lock(draft)

        Version.objects.filter(pk=draft.pk).delete()

        assert not Version.objects.filter(pk=draft.pk).exists()

    def test_publishing_a_pending_version_publishes_it_as_a_draft_is(self, document):
        version = lock(VersionFactory(document=document, markdown="# Heading"))

        version.publish()

        version.refresh_from_db()
        assert version.status == Version.Status.CURRENT
        assert version.number is not None
        assert version.published_at is not None
        assert "<h1>Heading</h1>" in version.html

    def test_publishing_a_pending_version_supersedes_the_one_in_force(
        self, published_version
    ):
        pending = lock(
            VersionFactory(document=published_version.document, markdown="Newer")
        )

        pending.publish()

        published_version.refresh_from_db()
        assert published_version.status == Version.Status.SUPERSEDED

    def test_publishing_a_pending_version_that_repeats_the_one_in_force_is_refused(
        self, document
    ):
        pending = lock(VersionFactory(document=document, markdown="Same"))
        VersionFactory(document=document, markdown="Same").publish()

        with pytest.raises(PublishError):
            pending.publish()

        pending.refresh_from_db()
        assert pending.status == Version.Status.PENDING

    def test_publishing_the_draft_leaves_the_pending_version_pending(self, document):
        pending = lock(VersionFactory(document=document, markdown="Pending"))
        draft = VersionFactory(document=document, markdown="Draft")

        draft.publish()

        pending.refresh_from_db()
        assert pending.status == Version.Status.PENDING

    def test_returning_a_pending_version_to_draft_makes_it_editable_again(self, draft):
        lock(draft)

        draft.return_to_draft()

        draft.refresh_from_db()
        assert draft.status == Version.Status.DRAFT
        draft.markdown = "Revised"
        draft.save()
        assert Version.objects.get(pk=draft.pk).markdown == "Revised"

    @pytest.mark.parametrize("start", ["draft", "current", "superseded"])
    def test_returning_anything_but_a_pending_version_is_refused(self, start):
        version = VersionFactory()
        if start != "draft":
            version.publish()
        if start == "superseded":
            VersionFactory(document=version.document, markdown="Newer").publish()
        before = Version.objects.filter(pk=version.pk).values().get()

        with pytest.raises(PublishError):
            version.return_to_draft()

        assert Version.objects.filter(pk=version.pk).values().get() == before

    def test_returning_rechecks_the_stored_status_under_the_lock(self, draft):
        lock(draft)
        stale = Version.objects.get(pk=draft.pk)
        draft.publish()

        with pytest.raises(PublishError):
            stale.return_to_draft()

        draft.refresh_from_db()
        assert draft.status == Version.Status.CURRENT

    @pytest.mark.usefixtures("site_languages")
    def test_returning_to_draft_returns_every_translation_with_its_wording(self, draft):
        lock(draft)
        put_back = put_live(TranslationFactory(version=draft, language="de"))
        replaced = put_live(
            TranslationFactory(version=draft, language="fr", markdown="Erste")
        )
        put_live(TranslationFactory(version=draft, language="fr", markdown="Zweite"))
        already_draft = TranslationFactory(
            version=draft, language="de", markdown="Entwurf"
        )
        wording = {
            t.pk: (t.markdown, t.summary)
            for t in Translation.objects.filter(version=draft)
        }

        draft.return_to_draft()

        rows = list(Translation.objects.filter(version=draft))
        assert len(rows) == 4
        for row in rows:
            assert row.status == Translation.Status.DRAFT
            assert row.html == ""
            assert row.published_at is None
            assert row.publisher is None
            assert row.publisher_subject == ""
            assert (row.markdown, row.summary) == wording[row.pk]
        assert {put_back.pk, replaced.pk, already_draft.pk} <= set(wording)

    @pytest.mark.usefixtures("site_languages")
    def test_returning_to_draft_forgets_who_put_a_translation_live(self, draft, user):
        lock(draft)
        translation = put_live(TranslationFactory(version=draft), publisher=user)

        draft.return_to_draft()

        translation.refresh_from_db()
        assert translation.publisher is None
        assert translation.publisher_subject == ""

    @pytest.mark.usefixtures("site_languages")
    def test_a_refused_return_leaves_the_translations_alone(self, published_version):
        translation = put_live(TranslationFactory(version=published_version))
        before = Translation.objects.filter(pk=translation.pk).values().get()

        with pytest.raises(PublishError):
            published_version.return_to_draft()

        assert Translation.objects.filter(pk=translation.pk).values().get() == before

    def test_a_pending_version_is_not_published(self, draft):
        lock(draft)

        assert draft.is_published is False
        assert draft.publisher_display is None

    def test_the_querysets_tell_pending_from_draft_and_published(self, document):
        draft = VersionFactory(document=document, markdown="Draft")
        pending = lock(VersionFactory(document=document, markdown="Pending"))
        current = VersionFactory(document=document, markdown="Current")
        current.publish()

        assert list(Version.objects.pending()) == [pending]
        assert list(Version.objects.drafts()) == [draft]
        assert list(Version.objects.published()) == [current]

    def test_a_status_other_than_the_four_is_refused_by_the_database(self, draft):
        with pytest.raises(IntegrityError), transaction.atomic():
            Version.objects.filter(pk=draft.pk).update(status="locked")

    def test_a_pending_row_carrying_a_number_is_refused_by_the_database(self, draft):
        with pytest.raises(IntegrityError), transaction.atomic():
            Version.objects.filter(pk=draft.pk).update(
                status="pending", number="2026.1"
            )

    def test_a_pending_row_carrying_html_is_refused_by_the_database(self, draft):
        with pytest.raises(IntegrityError), transaction.atomic():
            Version.objects.filter(pk=draft.pk).update(
                status="pending", html="<p>x</p>"
            )


@pytest.mark.django_db
class TestPendingIsNotPublished:
    """Everything that ignores a draft ignores a pending version too (SC-007)."""

    def test_a_document_with_only_a_pending_version_is_not_in_force(self):
        document = DocumentFactory()
        lock(VersionFactory(document=document))

        assert document not in Document.objects.in_force()

    def test_a_pending_version_is_not_a_replacement(self, document):
        first = VersionFactory(document=document, markdown="First")
        first.publish()
        lock(VersionFactory(document=document, markdown="Second"))

        replaced = Version.objects.all().with_replaced_at().get(pk=first.pk)

        assert replaced.replaced_at is None

    def test_a_pending_version_is_left_out_of_what_has_been_published_since(
        self, user, document
    ):
        first = VersionFactory(document=document, markdown="First")
        first.publish()
        Acceptance.objects.record(user, first)
        lock(VersionFactory(document=document, markdown="Second"))

        assert not Version.objects.all().since_last_accepted_by(user).exists()

    def test_recording_against_a_pending_version_is_refused(self, user, draft):
        lock(draft)

        with pytest.raises(RecordError):
            Acceptance.objects.record(user, draft)

        assert not Acceptance.objects.exists()

    def test_a_pending_version_is_refused_and_nothing_in_the_batch_is_written(
        self, user, published_version, draft
    ):
        lock(draft)

        with pytest.raises(RecordError):
            Acceptance.objects.record_many(user, [published_version, draft])

        assert not Acceptance.objects.exists()

    def test_a_document_with_only_a_pending_version_is_outstanding_for_nobody(
        self, user
    ):
        document = DocumentFactory()
        lock(VersionFactory(document=document))

        assert document not in Document.objects.outstanding_for(user)
        assert document not in Document.objects.enforced_outstanding_for(user)
        assert not document.is_outstanding_for(user)

    def test_a_pending_version_beside_the_one_in_force_changes_nothing_outstanding(
        self, user, published_version
    ):
        lock(VersionFactory(document=published_version.document, markdown="Newer"))

        assert set(Document.objects.outstanding_for(user)) == {
            published_version.document
        }

    def test_a_pending_version_does_not_fix_the_slug(self, document):
        lock(VersionFactory(document=document))

        document.slug = "another-slug"
        document.save()

        assert Document.objects.get(pk=document.pk).slug == "another-slug"

    def test_a_pending_version_does_not_stand_in_for_the_agreed_version(
        self, user, published_version
    ):
        pending = lock(
            VersionFactory(document=published_version.document, markdown="Newer")
        )
        Acceptance.objects.record(user, published_version)

        assert Acceptance.objects.for_person(user).filter(version=pending).count() == 0


class TestOfferedLanguages:
    """The languages a site offers translations in (FR-001)."""

    @staticmethod
    def codes():
        return [code for code, _name in offered_languages()]

    def test_the_main_language_is_not_offered(self, site_languages):
        assert self.codes() == ["de", "fr"]

    def test_a_main_language_with_a_region_resolves_against_the_site_list(
        self, site_languages
    ):
        with override_settings(LANGUAGE_CODE="en-us"):
            assert "en" not in self.codes()

    def test_a_different_main_language_is_the_one_left_out(self, site_languages):
        with override_settings(LANGUAGE_CODE="de"):
            assert self.codes() == ["en", "fr"]

    def test_a_main_language_the_site_does_not_list_leaves_every_language_offered(
        self,
    ):
        with override_settings(
            LANGUAGES=[("de", "German"), ("fr", "French")], LANGUAGE_CODE="en"
        ):
            assert self.codes() == ["de", "fr"]

    def test_none_is_offered_while_the_site_has_not_set_its_languages(self):
        assert self.codes() == []

    def test_each_language_comes_with_the_name_the_site_gave_it(self, site_languages):
        assert offered_languages() == [("de", "German"), ("fr", "French")]

    def test_the_languages_are_read_when_asked_not_when_imported(self):
        assert self.codes() == []
        with override_settings(LANGUAGES=[("en", "English"), ("fr", "French")]):
            assert self.codes() == ["fr"]
        assert self.codes() == []


class TestLanguageName:
    """A language is named by the site, then by Django, then by its code."""

    def test_a_code_outside_djangos_list_is_named_by_the_sites_label(self):
        with override_settings(LANGUAGES=[("en", "English"), ("xx", "Klingon")]):
            assert language_name("xx") == "Klingon"

    def test_a_code_nobody_labelled_is_named_by_itself(self):
        with override_settings(LANGUAGES=[("en", "English")]):
            assert language_name("xx") == "xx"

    def test_the_sites_label_wins_over_djangos_name(self):
        with override_settings(LANGUAGES=[("en", "English"), ("de", "Deutsch (CH)")]):
            assert language_name("de") == "Deutsch (CH)"

    def test_a_language_the_site_no_longer_lists_is_named_by_django(self):
        with override_settings(LANGUAGES=[("en", "English")]):
            assert language_name("de") == "German"


def put_live(translation, publisher=None):
    """Put a translation live, as the admin's page will."""
    translation.publish(publisher=publisher)
    return translation


def snapshot_of_the_version_side(version):
    """Everything about a version and its acceptances, to compare later."""
    return (
        Version.objects.filter(pk=version.pk).values().get(),
        list(Acceptance.objects.filter(version=version).values()),
    )


def another_published_version(translation):
    """A published version other than the translation's own."""
    other = VersionFactory()
    other.publish()
    return other


#: A change to each frozen field, given the live translation it is made to.
FROZEN_CHANGES = {
    "version": another_published_version,
    "language": lambda t: "fr",
    "markdown": lambda t: "Changed",
    "summary": lambda t: "Changed",
    "html": lambda t: "<p>Changed</p>",
    "published_at": lambda t: t.published_at + timedelta(days=1),
    "publisher": lambda t: UserFactory(),
    "publisher_subject": lambda t: "9999",
}


@pytest.fixture
def pending_version(db):
    return lock(VersionFactory())


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestTranslation:
    """One wording of a pending or published version in one language (FS-015)."""

    def test_a_translation_of_a_pending_version_is_written_as_a_draft(
        self, pending_version
    ):
        translation = TranslationFactory(version=pending_version)

        translation.refresh_from_db()
        assert translation.status == Translation.Status.DRAFT
        assert translation.html == ""
        assert translation.published_at is None
        assert translation.publisher is None
        assert translation.publisher_subject == ""

    def test_a_translation_of_a_published_version_is_written_as_a_draft(
        self, published_version
    ):
        translation = TranslationFactory(version=published_version)

        assert translation.status == Translation.Status.DRAFT

    def test_a_translation_of_a_draft_version_is_refused_and_writes_nothing(
        self, draft
    ):
        with pytest.raises(TranslationError):
            TranslationFactory(version=draft)

        assert not Translation.objects.exists()

    def test_a_language_the_site_does_not_offer_is_refused_and_writes_nothing(
        self, pending_version
    ):
        with pytest.raises(TranslationError):
            TranslationFactory(version=pending_version, language="ja")

        assert not Translation.objects.exists()

    def test_the_main_language_is_refused_and_writes_nothing(self, pending_version):
        with pytest.raises(TranslationError):
            TranslationFactory(version=pending_version, language="en")

        assert not Translation.objects.exists()

    def test_a_draft_translation_is_writable(self, pending_version):
        translation = TranslationFactory(version=pending_version)

        translation.markdown = "Revised"
        translation.summary = "Revised summary"
        translation.save()
        Translation.objects.filter(pk=translation.pk).update(markdown="Again")

        assert Translation.objects.get(pk=translation.pk).markdown == "Again"

    def test_a_notice_is_translated_like_any_other_document(self):
        notice = VersionFactory(document=DocumentFactory(kind=Document.Kind.NOTICE))
        notice.publish()

        translation = put_live(TranslationFactory(version=notice))

        assert translation.status == Translation.Status.CURRENT

    def test_two_drafts_for_one_version_and_language_are_both_kept(
        self, pending_version
    ):
        first = TranslationFactory(version=pending_version, markdown="Erste")
        second = TranslationFactory(version=pending_version, markdown="Zweite")

        put_live(second)

        assert Translation.objects.count() == 2
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.status == Translation.Status.DRAFT
        assert second.status == Translation.Status.CURRENT

    def test_the_database_refuses_two_current_wordings_for_one_language(
        self, pending_version
    ):
        put_live(TranslationFactory(version=pending_version))
        other = TranslationFactory(version=pending_version, markdown="Anders")

        with pytest.raises(IntegrityError), transaction.atomic():
            Translation.objects.filter(pk=other.pk).update(
                status="current", html="<p>x</p>", published_at=timezone.now()
            )

    def test_the_database_refuses_a_draft_carrying_html(self, pending_version):
        translation = TranslationFactory(version=pending_version)

        with pytest.raises(IntegrityError), transaction.atomic():
            Translation.objects.filter(pk=translation.pk).update(html="<p>x</p>")

    def test_the_database_refuses_a_live_wording_with_no_html(self, pending_version):
        translation = TranslationFactory(version=pending_version)

        with pytest.raises(IntegrityError), transaction.atomic():
            Translation.objects.filter(pk=translation.pk).update(
                status="current", published_at=timezone.now()
            )

    def test_a_language_is_named_and_says_whether_it_is_still_offered(
        self, pending_version
    ):
        translation = TranslationFactory(version=pending_version, language="de")

        assert translation.language_name == "German"
        assert translation.is_offered is True
        with override_settings(LANGUAGES=[("en", "English"), ("fr", "French")]):
            assert translation.is_offered is False
        with override_settings(LANGUAGES=[("de", "German")], LANGUAGE_CODE="de"):
            assert translation.is_offered is False


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestPuttingATranslationLive:
    def test_publishing_stores_the_rendered_and_sanitised_html(self, published_version):
        translation = TranslationFactory(
            version=published_version, markdown="Hallo **Welt**<script>x()</script>"
        )

        put_live(translation)

        translation.refresh_from_db()
        assert translation.status == Translation.Status.CURRENT
        assert "<strong>Welt</strong>" in translation.html
        assert "<script" not in translation.html
        assert translation.published_at is not None

    def test_the_stored_html_is_what_the_renderer_made_at_that_moment(
        self, published_version
    ):
        translation = TranslationFactory(version=published_version, markdown="Hallo")

        with override_settings(
            MVP_COMPLIANCE_RENDERER="tests.test_models.UppercaseRenderer"
        ):
            put_live(translation)

        translation.refresh_from_db()
        assert translation.html == "<P>HALLO</P>"

    def test_publishing_records_the_publisher_and_their_subject(
        self, published_version, user
    ):
        translation = TranslationFactory(version=published_version)

        put_live(translation, publisher=user)

        translation.refresh_from_db()
        assert translation.publisher == user
        assert translation.publisher_subject == Acceptance.subject_of(user)

    def test_publishing_with_nobody_named_records_nobody(self, published_version):
        translation = put_live(TranslationFactory(version=published_version))

        translation.refresh_from_db()
        assert translation.publisher is None
        assert translation.publisher_subject == ""
        assert translation.publisher_display == "Unknown publisher"

    def test_an_unsaved_publisher_is_refused_before_anything_changes(
        self, published_version
    ):
        translation = TranslationFactory(version=published_version)

        with pytest.raises(RecordError):
            translation.publish(publisher=get_user_model()(username="unsaved"))

        translation.refresh_from_db()
        assert translation.status == Translation.Status.DRAFT

    def test_a_summary_is_refused_when_the_version_has_none(self, published_version):
        translation = TranslationFactory(version=published_version, summary="Neu")

        with pytest.raises(PublishError):
            translation.publish()

        translation.refresh_from_db()
        assert translation.status == Translation.Status.DRAFT

    def test_a_summary_is_accepted_when_the_version_has_one(self):
        version = VersionFactory(summary="What changed")
        version.publish()
        translation = TranslationFactory(version=version, summary="Was sich änderte")

        put_live(translation)

        translation.refresh_from_db()
        assert translation.summary == "Was sich änderte"

    def test_output_that_renders_empty_is_refused(self, published_version):
        translation = TranslationFactory(version=published_version, markdown="  \n ")

        with pytest.raises(PublishError):
            translation.publish()

        translation.refresh_from_db()
        assert translation.status == Translation.Status.DRAFT

    def test_a_translation_of_a_draft_version_cannot_be_put_live(self, pending_version):
        translation = TranslationFactory(version=pending_version)
        pending_version.return_to_draft()
        translation.refresh_from_db()

        with pytest.raises(PublishError):
            translation.publish()

    def test_a_language_the_site_stopped_offering_is_refused_and_kept(
        self, published_version
    ):
        translation = TranslationFactory(version=published_version, language="de")

        with (
            override_settings(LANGUAGES=[("en", "English"), ("fr", "French")]),
            pytest.raises(PublishError),
        ):
            translation.publish()

        translation.refresh_from_db()
        assert translation.status == Translation.Status.DRAFT

    def test_putting_a_wording_live_twice_is_refused(self, published_version):
        translation = put_live(TranslationFactory(version=published_version))
        before = Translation.objects.filter(pk=translation.pk).values().get()

        with pytest.raises(PublishError):
            translation.publish()

        assert Translation.objects.filter(pk=translation.pk).values().get() == before

    def test_the_stored_status_is_rechecked_before_publishing(self, published_version):
        translation = TranslationFactory(version=published_version)
        stale = Translation.objects.get(pk=translation.pk)
        put_live(translation)

        with pytest.raises(PublishError):
            stale.publish()

        assert Translation.objects.filter(status="current").count() == 1

    def test_a_second_wording_supersedes_the_first_which_keeps_every_field(
        self, published_version, user
    ):
        first = put_live(
            TranslationFactory(version=published_version, markdown="Erste"),
            publisher=user,
        )
        kept = Translation.objects.filter(pk=first.pk).values().get()

        second = put_live(
            TranslationFactory(version=published_version, markdown="Zweite")
        )

        first.refresh_from_db()
        second.refresh_from_db()
        assert second.status == Translation.Status.CURRENT
        assert first.status == Translation.Status.SUPERSEDED
        assert {
            **Translation.objects.filter(pk=first.pk).values().get(),
            "status": "current",
        } == kept
        replaced_at = (
            Translation.objects.with_replaced_at().get(pk=first.pk).replaced_at
        )
        assert replaced_at == second.published_at
        assert (
            Translation.objects.with_replaced_at().get(pk=second.pk).replaced_at is None
        )

    def test_a_second_language_does_not_supersede_the_first(self, published_version):
        german = put_live(TranslationFactory(version=published_version, language="de"))
        french = put_live(TranslationFactory(version=published_version, language="fr"))

        german.refresh_from_db()
        french.refresh_from_db()
        assert german.status == french.status == Translation.Status.CURRENT

    def test_a_wording_identical_to_the_current_one_is_refused(self, published_version):
        put_live(
            TranslationFactory(version=published_version, markdown="Hallo", summary="")
        )
        repeat = TranslationFactory(version=published_version, markdown="Hallo\r\n")

        with pytest.raises(PublishError):
            repeat.publish()

        repeat.refresh_from_db()
        assert repeat.status == Translation.Status.DRAFT

    def test_a_correction_to_the_summary_alone_goes_live_and_supersedes(self):
        version = VersionFactory(summary="What changed")
        version.publish()
        first = put_live(
            TranslationFactory(version=version, markdown="Hallo", summary="Alt")
        )
        correction = TranslationFactory(
            version=version, markdown="Hallo", summary="Neu"
        )

        put_live(correction)

        first.refresh_from_db()
        correction.refresh_from_db()
        assert first.status == Translation.Status.SUPERSEDED
        assert correction.status == Translation.Status.CURRENT

    def test_a_wording_is_not_a_repeat_of_one_in_another_language(
        self, published_version
    ):
        put_live(TranslationFactory(version=published_version, language="de"))

        french = put_live(
            TranslationFactory(
                version=published_version,
                language="fr",
                markdown=Translation.objects.get().markdown,
            )
        )

        assert french.status == Translation.Status.CURRENT

    def test_the_version_and_its_acceptances_are_unchanged_throughout(
        self, published_version, user
    ):
        Acceptance.objects.record(user, published_version)
        before = snapshot_of_the_version_side(published_version)

        translation = TranslationFactory(version=published_version)
        put_live(translation, publisher=user)
        put_live(TranslationFactory(version=published_version, markdown="Besser"))

        assert snapshot_of_the_version_side(published_version) == before

    def test_the_version_of_a_pending_translation_is_unchanged_throughout(
        self, pending_version
    ):
        before = snapshot_of_the_version_side(pending_version)

        put_live(TranslationFactory(version=pending_version))

        assert snapshot_of_the_version_side(pending_version) == before


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestTranslationIsLive:
    """A translation is live once its version is published (FR-006)."""

    def test_a_current_wording_of_a_pending_version_is_not_live(self, pending_version):
        translation = put_live(TranslationFactory(version=pending_version))

        assert translation not in Translation.objects.live()
        assert translation.live_since is None

    def test_it_is_live_once_the_version_is_published(self, pending_version):
        translation = put_live(TranslationFactory(version=pending_version))

        pending_version.publish()

        assert translation in Translation.objects.live()
        translation.refresh_from_db()
        assert translation.live_since == pending_version.published_at

    def test_a_wording_put_live_after_the_version_is_live_from_that_moment(
        self, published_version
    ):
        translation = put_live(TranslationFactory(version=published_version))

        assert translation in Translation.objects.live()
        assert translation.live_since == translation.published_at

    def test_a_draft_is_never_live(self, published_version):
        translation = TranslationFactory(version=published_version)

        assert translation not in Translation.objects.live()
        assert translation.live_since is None

    def test_a_wording_replaced_before_the_version_was_published_was_never_live(
        self, pending_version
    ):
        first = put_live(TranslationFactory(version=pending_version, markdown="Erste"))
        second = put_live(
            TranslationFactory(version=pending_version, markdown="Zweite")
        )

        pending_version.publish()

        first.refresh_from_db()
        second.refresh_from_db()
        assert first.live_since is None
        assert second.live_since == pending_version.published_at
        assert list(Translation.objects.live()) == [second]

    def test_a_wording_replaced_after_the_version_was_published_was_live(
        self, published_version
    ):
        first = put_live(TranslationFactory(version=published_version, markdown="A"))
        put_live(TranslationFactory(version=published_version, markdown="B"))

        first.refresh_from_db()
        assert first.live_since == first.published_at
        assert first not in Translation.objects.live()

    def test_a_superseded_wording_is_not_live(self, published_version):
        first = put_live(TranslationFactory(version=published_version, markdown="A"))
        put_live(TranslationFactory(version=published_version, markdown="B"))

        assert first not in Translation.objects.live()


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestTranslationImmutability:
    """A wording that has been live can never change or go (FR-008, SC-003)."""

    @pytest.fixture
    def live(self, published_version, user):
        return put_live(TranslationFactory(version=published_version), publisher=user)

    @pytest.mark.parametrize("field", list(FROZEN_CHANGES))
    def test_saving_a_changed_frozen_field_is_refused(self, live, field):
        before = Translation.objects.filter(pk=live.pk).values().get()
        setattr(live, field, FROZEN_CHANGES[field](live))

        with pytest.raises(PublishedTranslationError):
            live.save()

        assert Translation.objects.filter(pk=live.pk).values().get() == before

    @pytest.mark.parametrize("field", list(FROZEN_CHANGES))
    def test_updating_a_frozen_field_is_refused(self, live, field):
        before = Translation.objects.filter(pk=live.pk).values().get()
        value = FROZEN_CHANGES[field](live)
        key = field if not hasattr(value, "pk") else f"{field}_id"
        value = value.pk if hasattr(value, "pk") else value

        with pytest.raises(PublishedTranslationError):
            Translation.objects.filter(pk=live.pk).update(**{key: value})

        assert Translation.objects.filter(pk=live.pk).values().get() == before

    def test_a_superseded_wording_stays_frozen(self, published_version, live):
        put_live(TranslationFactory(version=published_version, markdown="Besser"))
        live.refresh_from_db()
        assert live.status == Translation.Status.SUPERSEDED

        with pytest.raises(PublishedTranslationError):
            Translation.objects.filter(pk=live.pk).update(markdown="Changed")
        live.markdown = "Changed"
        with pytest.raises(PublishedTranslationError):
            live.save()

    def test_a_bulk_upsert_of_a_live_wording_is_refused(self, live):
        before = Translation.objects.filter(pk=live.pk).values().get()
        changed = Translation.objects.get(pk=live.pk)
        changed.markdown = "Changed"

        with pytest.raises(PublishedTranslationError):
            Translation.objects.bulk_create(
                [changed],
                update_conflicts=True,
                unique_fields=["id"],
                update_fields=["markdown"],
            )

        assert Translation.objects.filter(pk=live.pk).values().get() == before

    def test_a_bulk_upsert_of_a_draft_is_allowed(self, published_version):
        draft = TranslationFactory(version=published_version)
        draft.markdown = "Revised"

        Translation.objects.bulk_create(
            [draft],
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=["markdown"],
        )

        assert Translation.objects.get(pk=draft.pk).markdown == "Revised"

    def test_the_standing_of_a_live_wording_may_still_change(self, live):
        Translation.objects.filter(pk=live.pk).update(status="superseded")

        assert Translation.objects.get(pk=live.pk).status == "superseded"

    def test_deleting_a_live_wording_is_refused(self, live):
        with pytest.raises(PublishedTranslationError):
            live.delete()
        with pytest.raises(PublishedTranslationError):
            Translation.objects.filter(pk=live.pk).delete()
        with pytest.raises(PublishedTranslationError):
            Translation.objects.all().delete()

        assert Translation.objects.filter(pk=live.pk).exists()

    def test_deleting_a_superseded_wording_is_refused(self, published_version, live):
        put_live(TranslationFactory(version=published_version, markdown="Besser"))

        with pytest.raises(PublishedTranslationError):
            Translation.objects.filter(pk=live.pk).delete()

    def test_a_draft_may_be_deleted(self, published_version):
        draft = TranslationFactory(version=published_version)

        draft.delete()

        assert not Translation.objects.exists()

    def test_a_published_version_cannot_be_deleted_with_its_translations(self, live):
        with pytest.raises(PublishedVersionError):
            live.version.delete()

        assert Translation.objects.filter(pk=live.pk).exists()

    def test_a_wording_put_live_on_a_pending_version_is_not_yet_frozen(
        self, pending_version
    ):
        translation = put_live(TranslationFactory(version=pending_version))

        Translation.objects.filter(pk=translation.pk).update(
            status="draft", html="", published_at=None, publisher=None
        )

        assert Translation.objects.get(pk=translation.pk).status == "draft"

    def test_discarding_a_pending_version_discards_its_translations(
        self, pending_version
    ):
        put_live(TranslationFactory(version=pending_version, language="de"))
        TranslationFactory(version=pending_version, language="fr")

        pending_version.delete()

        assert not Translation.objects.exists()

    def test_a_wording_frozen_by_its_version_being_published_is_frozen_from_then(
        self, pending_version
    ):
        translation = put_live(TranslationFactory(version=pending_version))
        pending_version.publish()

        with pytest.raises(PublishedTranslationError):
            Translation.objects.filter(pk=translation.pk).update(markdown="Changed")


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestTranslationPublisher:
    def test_removing_the_publishers_account_keeps_who_it_was(
        self, published_version, user
    ):
        translation = put_live(
            TranslationFactory(version=published_version), publisher=user
        )
        subject = Acceptance.subject_of(user)

        user.delete()

        translation.refresh_from_db()
        assert translation.publisher is None
        assert translation.publisher_subject == subject
        assert translation.publisher_display == "Account removed"

    def test_a_publisher_is_named(self, published_version, user):
        translation = put_live(
            TranslationFactory(version=published_version), publisher=user
        )

        assert translation.publisher_display == str(user)

    def test_a_draft_has_no_publisher_to_display(self, published_version):
        assert TranslationFactory(version=published_version).publisher_display is None


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestHistoricalTranslation:
    """The historical model carries the guards too (docs/adr/0004)."""

    @pytest.fixture
    def historical(self):
        loader = MigrationLoader(connection)
        (leaf,) = loader.graph.leaf_nodes(app="mvp_compliance")
        return loader.project_state(leaf).apps.get_model(
            "mvp_compliance", "Translation"
        )

    @pytest.fixture
    def live(self, published_version):
        return put_live(TranslationFactory(version=published_version))

    def test_a_migration_cannot_change_a_live_wording(self, historical, live):
        with pytest.raises(PublishedTranslationError):
            historical.objects.filter(pk=live.pk).update(markdown="Changed")
        with pytest.raises(PublishedTranslationError):
            historical.objects.filter(pk=live.pk).update(html="<p>Other</p>")

        assert historical.objects.get(pk=live.pk).markdown == live.markdown

    def test_a_migration_cannot_delete_a_live_wording(self, historical, live):
        with pytest.raises(PublishedTranslationError):
            historical.objects.filter(pk=live.pk).delete()

        assert historical.objects.filter(pk=live.pk).exists()

    def test_a_migration_can_edit_a_draft(self, historical, published_version):
        draft = TranslationFactory(version=published_version)

        historical.objects.filter(pk=draft.pk).update(markdown="Changed")

        assert historical.objects.get(pk=draft.pk).markdown == "Changed"


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestMissingTranslation:
    """Which versions still lack a live translation (FR-011)."""

    def test_it_lists_pending_and_published_versions_and_never_drafts(self, document):
        draft = VersionFactory(document=document, markdown="Draft")
        pending = lock(VersionFactory(document=document, markdown="Pending"))
        current = VersionFactory(document=document, markdown="Current")
        current.publish()
        superseded = VersionFactory(document=DocumentFactory())
        superseded.publish()
        VersionFactory(document=superseded.document, markdown="Newer").publish()

        missing = set(Version.objects.missing_translation("de"))

        assert draft not in missing
        assert {pending, current, superseded} <= missing

    def test_a_version_with_a_current_wording_in_the_language_is_not_listed(
        self, published_version
    ):
        put_live(TranslationFactory(version=published_version, language="de"))

        assert published_version not in Version.objects.missing_translation("de")

    def test_a_current_wording_of_a_pending_version_counts(self, pending_version):
        put_live(TranslationFactory(version=pending_version, language="de"))

        assert pending_version not in Version.objects.missing_translation("de")

    def test_a_draft_wording_does_not_count(self, published_version):
        TranslationFactory(version=published_version, language="de")

        assert published_version in Version.objects.missing_translation("de")

    def test_another_language_does_not_count(self, published_version):
        put_live(TranslationFactory(version=published_version, language="fr"))

        assert published_version in Version.objects.missing_translation("de")
        assert published_version not in Version.objects.missing_translation("fr")

    def test_with_no_language_it_covers_every_offered_language(self):
        both = VersionFactory()
        both.publish()
        only_german = VersionFactory()
        only_german.publish()
        none = VersionFactory()
        none.publish()
        put_live(TranslationFactory(version=both, language="de"))
        put_live(TranslationFactory(version=both, language="fr"))
        put_live(TranslationFactory(version=only_german, language="de"))

        missing = list(Version.objects.missing_translation())

        assert both not in missing
        assert missing.count(only_german) == 1
        assert missing.count(none) == 1

    def test_with_no_languages_offered_nothing_is_missing(self, published_version):
        with override_settings(LANGUAGES=[("en", "English")]):
            assert not Version.objects.missing_translation().exists()

    def test_it_narrows_a_documents_own_versions(self, document):
        first = VersionFactory(document=document, markdown="First")
        first.publish()
        second = VersionFactory(document=document, markdown="Second")
        second.publish()
        put_live(TranslationFactory(version=second, language="de"))

        assert list(document.versions.missing_translation("de")) == [first]

    def test_it_reads_in_one_query(self, published_version):
        lock(VersionFactory(markdown="Pending"))

        with CaptureQueriesContext(connection) as queries:
            list(Version.objects.missing_translation())
            list(Version.objects.missing_translation("de"))

        assert len(queries) == 2


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestTranslationFromCode:
    """The route the admin uses is public: a developer calls it directly (FS-015)."""

    def test_create_then_publish_gives_the_row_the_admin_gives(self, pending_version):
        translation = Translation.objects.create(
            version=pending_version, language="de", markdown="Hallo **Welt**"
        )
        translation.publish()

        stored = Translation.objects.get(pk=translation.pk)
        assert stored.status == Translation.Status.CURRENT
        assert "<strong>Welt</strong>" in stored.html
        assert stored.published_at is not None
        assert stored.publisher is None
        assert stored.publisher_subject == ""
        nobody_named = VersionFactory()
        nobody_named.publish()
        assert stored.publisher_display == nobody_named.publisher_display

    def test_an_account_passed_to_publish_is_the_one_named(self, pending_version, user):
        translation = Translation.objects.create(
            version=pending_version, language="de", markdown="Hallo"
        )
        translation.publish(publisher=user)

        stored = Translation.objects.get(pk=translation.pk)
        assert stored.publisher == user
        assert stored.publisher_subject == Acceptance.subject_of(user)

    def test_a_correction_from_code_keeps_the_earlier_wording(self, pending_version):
        first = Translation.objects.create(
            version=pending_version, language="de", markdown="Erster Text"
        )
        first.publish()
        correction = Translation.objects.create(
            version=pending_version, language="de", markdown="Besserer Text"
        )
        correction.publish()

        first.refresh_from_db()
        correction.refresh_from_db()
        assert first.status == Translation.Status.SUPERSEDED
        assert first.markdown == "Erster Text"
        assert "Erster Text" in first.html
        assert correction.status == Translation.Status.CURRENT

    @pytest.mark.parametrize(
        "language", ["fr-ca", "en"], ids=["not-offered", "main-language"]
    )
    def test_a_language_not_offered_raises_and_writes_nothing(
        self, pending_version, language
    ):
        with pytest.raises(TranslationError):
            Translation.objects.create(
                version=pending_version, language=language, markdown="Hallo"
            )

        assert not Translation.objects.exists()

    def test_a_draft_version_raises_and_writes_nothing(self, draft):
        with pytest.raises(TranslationError):
            Translation.objects.create(version=draft, language="de", markdown="Hallo")

        assert not Translation.objects.exists()

    def test_publishing_an_already_published_row_raises_and_writes_nothing(
        self, pending_version
    ):
        translation = Translation.objects.create(
            version=pending_version, language="de", markdown="Hallo"
        )
        translation.publish()
        before = Translation.objects.filter(pk=translation.pk).values().get()

        with pytest.raises(PublishError):
            translation.publish()

        assert Translation.objects.filter(pk=translation.pk).values().get() == before
        assert Translation.objects.count() == 1


@pytest.mark.django_db
class TestStaleInstanceIsRefused:
    """An instance that differs from the stored row is refused, writing and sending nothing (FR-020)."""

    @pytest.fixture
    def stale(self, draft):
        """An instance of ``draft`` read before another writer changed it."""
        copy = Version.objects.get(pk=draft.pk)
        Version.objects.filter(pk=draft.pk).update(
            markdown="Changed elsewhere", summary="Summary changed elsewhere"
        )
        return copy

    @pytest.mark.parametrize("field", ["markdown", "summary"])
    def test_locking_an_instance_that_differs_from_the_stored_row_is_refused(
        self, django_capture_on_commit_callbacks, draft, field
    ):
        stale = Version.objects.get(pk=draft.pk)
        Version.objects.filter(pk=draft.pk).update(**{field: "Changed elsewhere"})
        before = Version.objects.filter(pk=draft.pk).values().get()

        with (
            django_capture_on_commit_callbacks(execute=True) as callbacks,
            pytest.raises(PublishError),
        ):
            stale.lock_for_translation()

        assert Version.objects.filter(pk=draft.pk).values().get() == before
        assert callbacks == []

    def test_publishing_an_instance_that_differs_from_the_stored_row_is_refused(
        self, django_capture_on_commit_callbacks, draft, stale
    ):
        before = Version.objects.filter(pk=draft.pk).values().get()

        with (
            django_capture_on_commit_callbacks(execute=True) as callbacks,
            pytest.raises(PublishError),
        ):
            stale.publish()

        assert Version.objects.filter(pk=draft.pk).values().get() == before
        assert callbacks == []

    def test_an_instance_that_matches_the_stored_row_still_locks_and_publishes(
        self, document
    ):
        locked = VersionFactory(document=document, markdown="One")
        published = VersionFactory(document=document, markdown="Two")

        Version.objects.get(pk=locked.pk).lock_for_translation()
        Version.objects.get(pk=published.pk).publish()

        assert Version.objects.get(pk=locked.pk).status == Version.Status.PENDING
        assert Version.objects.get(pk=published.pk).status == Version.Status.CURRENT


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestReturningToDraftLocksTheVersion:
    """A translation put live as the version returns is either returned or refused (FR-022)."""

    def test_the_document_then_the_version_are_locked_before_translations_are_read(
        self, pending_version
    ):
        events = []
        real_select_for_update = QuerySet.select_for_update
        real_iterator = QuerySet._fetch_all

        def spy_lock(queryset, *args, **kwargs):
            events.append(("lock", queryset.model))
            return real_select_for_update(queryset, *args, **kwargs)

        def spy_read(queryset):
            if queryset.model is Translation and not queryset._result_cache:
                events.append(("read", queryset.model))
            return real_iterator(queryset)

        with (
            patch.object(QuerySet, "select_for_update", spy_lock),
            patch.object(QuerySet, "_fetch_all", spy_read),
        ):
            pending_version.return_to_draft()

        assert events.index(("lock", Document)) < events.index(("lock", Version))
        assert events.index(("lock", Version)) < events.index(("read", Translation))

    def test_a_translation_put_live_after_the_version_returned_is_refused(
        self, pending_version
    ):
        waiting = TranslationFactory(version=pending_version, language="de")
        pending_version.return_to_draft()

        with pytest.raises(PublishError):
            waiting.publish()

        row = Translation.objects.get(pk=waiting.pk)
        assert row.status == Translation.Status.DRAFT
        assert row.html == ""
