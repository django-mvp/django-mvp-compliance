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

    def test_it_offers_public_urls_for_a_project_to_mount(self) -> None:
        """FS-006 decisions.md D4: supersedes FS-002's D11 and FS-004's T031.
        The package now has addresses a visitor can reach, the published
        documents, and the host project mounts them under its own prefix."""
        assert importlib.util.find_spec("mvp_compliance.urls") is not None

        from mvp_compliance import urls

        assert urls.app_name == "mvp_compliance"

    def test_it_registers_both_models_in_the_admin(self) -> None:
        """D11: replaces FS-001's assertion that no admin exists — FS-002 is
        the feature that adds one."""
        from django.contrib import admin

        from mvp_compliance.models import Document, Version

        assert Document in admin.site._registry
        assert Version in admin.site._registry

    def test_the_disclosure_proxy_is_registered_and_acceptance_is_not(self) -> None:
        """T031, decisions.md D7: no changelist of anybody's records.

        ``Disclosure`` gets the admin index entry, an address and a
        permission; registering ``Acceptance`` itself would hand everyone
        holding ``view_acceptance`` a changelist of every person's consent
        history.
        """
        from django.contrib import admin

        from mvp_compliance.models import Acceptance, Disclosure

        assert Disclosure in admin.site._registry
        assert Acceptance not in admin.site._registry
