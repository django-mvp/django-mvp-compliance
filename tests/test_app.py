"""The package installs and exposes what a consuming project needs from it."""

import importlib.util

from django.apps import apps


class TestPackagedApp:
    def test_app_is_installed(self) -> None:
        assert apps.is_installed("mvp_compliance")

    def test_app_label_is_stable(self) -> None:
        # Changing the label renames tables that already hold consent records.
        assert apps.get_app_config("mvp_compliance").label == "mvp_compliance"

    def test_it_registers_no_public_urls(self) -> None:
        assert importlib.util.find_spec("mvp_compliance.urls") is None

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
