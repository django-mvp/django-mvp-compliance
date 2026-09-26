"""The demo's navigation: the pages a visitor reads, as a host project would add them."""

from flex_menu import MenuItem
from mvp.menus import AppMenu

AppMenu.append(
    MenuItem(
        name="legal-documents",
        view_name="mvp_compliance:index",
        extra_context={"label": "Legal documents", "icon": "file-earmark-text"},
    )
)
