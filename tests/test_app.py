"""The package installs and exposes what a consuming project needs from it."""

import importlib.util

import pytest
from django.apps import apps


class TestPackagedApp:
    def test_app_is_installed(self) -> None:
        assert apps.is_installed("mvp_compliance")

    def test_app_label_is_stable(self) -> None:
        # Changing the label renames tables that already hold consent records.
        assert apps.get_app_config("mvp_compliance").label == "mvp_compliance"

    def test_it_offers_public_urls_for_a_project_to_mount(self) -> None:
        assert importlib.util.find_spec("mvp_compliance.urls") is not None

        from mvp_compliance import urls

        assert urls.app_name == "mvp_compliance"

    def test_it_registers_both_models_in_the_admin(self) -> None:
        from django.contrib import admin

        from mvp_compliance.models import Document, Version

        assert Document in admin.site._registry
        assert Version in admin.site._registry

    def test_the_disclosure_proxy_is_registered_and_acceptance_is_not(self) -> None:
        from django.contrib import admin

        from mvp_compliance.models import Acceptance, Disclosure

        assert Disclosure in admin.site._registry
        assert Acceptance not in admin.site._registry


@pytest.mark.django_db
class TestDeclaredDocumentsAfterMigrate:
    def test_migrating_creates_the_declared_documents(self, settings) -> None:
        from django.core.management import call_command

        from mvp_compliance.models import Document

        settings.MVP_COMPLIANCE_DOCUMENTS = {"privacy-policy": "Privacy policy"}

        call_command("migrate", verbosity=0)

        assert Document.objects.filter(slug="privacy-policy").exists()
