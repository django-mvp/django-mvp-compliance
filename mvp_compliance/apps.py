"""The app configuration."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MvpComplianceConfig(AppConfig):
    """Registers the package as the ``mvp_compliance`` app."""

    name = "mvp_compliance"
    label = "mvp_compliance"
    verbose_name = _("Compliance")
