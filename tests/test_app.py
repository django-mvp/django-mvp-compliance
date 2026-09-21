"""The package installs and exposes what a consuming project needs from it."""

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
