"""Creating the documents a host project declares after it migrates."""

import pytest
from django.apps import apps as global_apps
from django.apps.registry import Apps
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from mvp_compliance.management import create_declared_documents
from mvp_compliance.models import Acceptance, Document, Version
from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    UserFactory,
    VersionFactory,
)

DECLARED = {"privacy-policy": "Privacy policy", "terms-of-use": "Terms of use"}


def run(**kwargs) -> None:
    create_declared_documents(global_apps.get_app_config("mvp_compliance"), **kwargs)


@pytest.mark.django_db
class TestCreateDeclaredDocuments:
    def test_each_missing_document_is_created_with_its_slug_and_name(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED

        run()

        assert dict(Document.objects.values_list("slug", "name")) == DECLARED

    def test_a_created_document_has_no_version(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED

        run()

        assert not Version.objects.exists()

    def test_kind_and_enforcement_are_the_model_defaults(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED
        default = Document()

        run()

        for document in Document.objects.all():
            assert document.kind == default.kind
            assert document.enforced == default.enforced

    def test_a_declared_document_without_a_version_has_no_page(self, client, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED
        run()

        response = client.get(
            reverse("mvp_compliance:document", args=["privacy-policy"])
        )

        assert response.status_code == 404

    def test_a_declared_document_without_a_version_is_not_in_force(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED
        run()

        assert not Document.objects.in_force().exists()

    def test_a_declared_document_without_a_version_is_outstanding_for_nobody(
        self, settings
    ):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED
        run()

        assert not Document.objects.outstanding_for(UserFactory()).exists()

    def test_a_second_call_creates_nothing(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED
        run()

        run()

        assert Document.objects.count() == len(DECLARED)

    def test_a_second_call_leaves_name_kind_and_enforcement_as_they_were(
        self, settings
    ):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED
        run()
        Document.objects.filter(slug="privacy-policy").update(
            name="Data protection", kind=Document.Kind.NOTICE, enforced=False
        )

        run()

        document = Document.objects.get(slug="privacy-policy")
        assert document.name == "Data protection"
        assert document.kind == Document.Kind.NOTICE
        assert document.enforced is False

    def test_a_document_with_the_declared_slug_is_left_as_it_is(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = {"privacy-policy": "Privacy policy"}
        document = DocumentFactory(
            slug="privacy-policy", name="Our policy", enforced=False
        )
        version = VersionFactory(document=document)
        version.publish()
        acceptance = AcceptanceFactory(version=version)

        run()

        document.refresh_from_db()
        assert (document.name, document.kind, document.enforced) == (
            "Our policy",
            Document.Kind.AGREED,
            False,
        )
        assert list(document.versions.values_list("pk", flat=True)) == [version.pk]
        assert list(Acceptance.objects.values_list("pk", flat=True)) == [acceptance.pk]

    def test_dropping_a_declaration_leaves_the_document(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED
        run()
        settings.MVP_COMPLIANCE_DOCUMENTS = {"terms-of-use": "Terms of use"}

        run()

        assert Document.objects.filter(slug="privacy-policy").exists()

    def test_nothing_declared_creates_nothing(self):
        run()

        assert not Document.objects.exists()

    def test_an_unset_declaration_and_an_empty_one_are_the_same(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = {}

        run()

        assert not Document.objects.exists()

    def test_apps_without_the_model_do_nothing(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED

        run(apps=Apps())

        assert not Document.objects.exists()

    def test_publishing_a_declared_document_fills_its_address(self, client, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = DECLARED
        run()
        document = Document.objects.get(slug="privacy-policy")
        version = VersionFactory(document=document)
        version.publish()

        response = client.get(
            reverse("mvp_compliance:document", args=["privacy-policy"])
        )

        assert response.status_code == 200
        assert response.context["version"] == version


@pytest.mark.django_db
class TestRefusedDeclarations:
    def test_a_name_belonging_to_another_slug_is_refused_naming_both(self, settings):
        DocumentFactory(slug="data-protection", name="Privacy policy")
        settings.MVP_COMPLIANCE_DOCUMENTS = {"privacy-policy": "Privacy policy"}

        with pytest.raises(ImproperlyConfigured) as refused:
            run()

        assert "privacy-policy" in str(refused.value)
        assert "data-protection" in str(refused.value)

    def test_one_fault_stops_the_valid_declarations_too(self, settings):
        DocumentFactory(slug="data-protection", name="Privacy policy")
        settings.MVP_COMPLIANCE_DOCUMENTS = {
            "privacy-policy": "Privacy policy",
            "terms-of-use": "Terms of use",
        }

        with pytest.raises(ImproperlyConfigured):
            run()

        assert not Document.objects.filter(slug="terms-of-use").exists()

    @pytest.mark.parametrize(
        ("slug", "name"),
        [
            ("Privacy-Policy", "Privacy policy"),
            ("agree", "Agree"),
            ("privacy-policy", ""),
            ("privacy-policy", "Privacy policy "),
            ("privacy-policy", " Privacy policy"),
        ],
        ids=["capital", "reserved", "empty-name", "trailing-space", "leading-space"],
    )
    def test_a_declaration_the_model_would_refuse_creates_nothing(
        self, settings, slug, name
    ):
        settings.MVP_COMPLIANCE_DOCUMENTS = {slug: name, "terms-of-use": "Terms"}

        with pytest.raises(ImproperlyConfigured) as refused:
            run()

        assert slug in str(refused.value)
        assert not Document.objects.exists()

    def test_every_fault_is_named_in_one_refusal(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = {"Bad-Slug": "One", "agree": "Two"}

        with pytest.raises(ImproperlyConfigured) as refused:
            run()

        assert "Bad-Slug" in str(refused.value)
        assert "agree" in str(refused.value)

    def test_two_declarations_sharing_a_name_are_refused(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = {
            "privacy-policy": "Policy",
            "terms-of-use": "Policy",
        }

        with pytest.raises(ImproperlyConfigured) as refused:
            run()

        assert "privacy-policy" in str(refused.value)
        assert "terms-of-use" in str(refused.value)
        assert not Document.objects.exists()

    def test_a_name_that_is_already_its_own_documents_is_not_a_fault(self, settings):
        DocumentFactory(slug="privacy-policy", name="Privacy policy")
        settings.MVP_COMPLIANCE_DOCUMENTS = {
            "privacy-policy": "Privacy policy",
            "terms-of-use": "Terms of use",
        }

        run()

        assert Document.objects.filter(slug="terms-of-use").exists()

    def test_a_fault_in_an_existing_documents_declaration_is_ignored(self, settings):
        DocumentFactory(slug="privacy-policy", name="Our policy")
        settings.MVP_COMPLIANCE_DOCUMENTS = {"privacy-policy": "Privacy policy "}

        run()

        assert Document.objects.get(slug="privacy-policy").name == "Our policy"
