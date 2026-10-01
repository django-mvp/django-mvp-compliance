"""The package's entry in the account area's menu.

An entry whose address does not resolve is dropped by the menu, so a project
that does not mount the package's pages gets no entry and no failure.
"""

from django.utils.translation import gettext_lazy as _
from flex_menu import MenuItem
from mvp.menus import AccountCenterMenu

AccountCenterMenu.append(
    MenuItem(
        name="agreed-documents",
        view_name="mvp_compliance:agreed",
        extra_context={"label": _("Agreements"), "icon": "document"},
    )
)
