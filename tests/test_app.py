"""The package installs and exposes what a consuming project needs from it."""

import importlib.util

from django.apps import apps


class TestPackagedApp:
    """What a host project gets after installing and adding it to INSTALLED_APPS."""

    def test_app_is_installed(self) -> None:
        assert apps.is_installed("mvp_compliance")

    def test_app_label_is_stable(self) -> None:
        """The label prefixes every table and every permission codename.

        Changing it later renames tables that already hold consent records, so
        it is pinned here rather than left to Django's default derivation.
        """
        assert apps.get_app_config("mvp_compliance").label == "mvp_compliance"

    def test_it_registers_no_public_urls(self) -> None:
        """D11: FS-002 supersedes FS-001's D5. The model layer's scope is gone —
        FS-002 is the authoring surface — but the package still serves no
        address a visitor can reach directly (FR-008)."""
        assert importlib.util.find_spec("mvp_compliance.urls") is None

    def test_it_registers_both_models_in_the_admin(self) -> None:
        """D11: replaces FS-001's assertion that no admin exists — FS-002 is
        the feature that adds one."""
        from django.contrib import admin

        from mvp_compliance.models import Document, Version

        assert Document in admin.site._registry
        assert Version in admin.site._registry
