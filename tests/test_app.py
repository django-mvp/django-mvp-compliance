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

    def test_it_ships_no_admin_forms_views_or_urls(self) -> None:
        """D5: this package registers no admin, ships no forms, no views and no URLs."""
        for module_name in ("admin", "forms", "views", "urls"):
            assert importlib.util.find_spec(f"mvp_compliance.{module_name}") is None, (
                f"mvp_compliance.{module_name} should not exist"
            )

    def test_it_registers_nothing_in_the_admin(self) -> None:
        from django.contrib import admin

        from mvp_compliance.models import Document, Version

        assert Document not in admin.site._registry
        assert Version not in admin.site._registry
