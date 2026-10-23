"""The app configuration."""

from django.apps import AppConfig
from django.core.checks import register
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


class MvpComplianceConfig(AppConfig):
    """Registers the package as the ``mvp_compliance`` app."""

    name = "mvp_compliance"
    label = "mvp_compliance"
    verbose_name = _("Compliance")

    def ready(self):
        """Register the checks and create the declared documents."""
        # Not at module level: these need the app registry.
        from mvp_compliance.checks import (
            check_agreement_middleware,
            check_personal_data,
        )
        from mvp_compliance.management import create_declared_documents

        register(check_agreement_middleware)
        register(check_personal_data)
        post_migrate.connect(create_declared_documents, sender=self)
