"""The app configuration."""

from django.apps import AppConfig
from django.core.checks import register
from django.utils.translation import gettext_lazy as _


class MvpComplianceConfig(AppConfig):
    """Registers the package as the ``mvp_compliance`` app."""

    name = "mvp_compliance"
    label = "mvp_compliance"
    verbose_name = _("Compliance")

    def ready(self):
        """Register the checks that report a misconfigured agreement check."""
        # Not at module level: the auth middleware needs the app registry.
        from mvp_compliance.checks import check_agreement_middleware

        register(check_agreement_middleware)
