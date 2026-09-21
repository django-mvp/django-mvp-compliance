from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MvpComplianceConfig(AppConfig):
    name = "mvp_compliance"
    label = "mvp_compliance"
    verbose_name = _("Compliance")
