"""Creating the documents a host project declares after it migrates."""

import pytest
from django.apps import apps as global_apps
from django.apps.registry import Apps
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
