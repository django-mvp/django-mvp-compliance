"""The demo's navigation: the pages a visitor reads, as a host project would add them."""

from django.urls import reverse_lazy
from flex_menu import MenuItem
from mvp.menus import AppMenu

AppMenu.append(
    MenuItem(
        name="legal-documents",
        url=reverse_lazy("mvp_compliance:document", args=["privacy-policy"]),
        extra_context={"label": "Legal documents", "icon": "file-earmark-text"},
    )
)
