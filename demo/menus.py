"""The demo's navigation: its own pages, and the pages a visitor reads, as a host project would add them."""

from django.urls import reverse_lazy
from flex_menu import MenuItem
from mvp.menus import AppMenu

AppMenu.extend(
    [
        MenuItem(
            name="overview",
            view_name="overview",
            extra_context={"label": "Overview", "icon": "overview"},
        ),
        MenuItem(
            name="documents",
            view_name="documents",
            extra_context={"label": "Documents", "icon": "document"},
        ),
        MenuItem(
            name="agreeing",
            view_name="agreeing",
            extra_context={"label": "Agreeing", "icon": "check"},
        ),
        MenuItem(
            name="sign-in-accounts",
            view_name="sign_in_accounts",
            extra_context={"label": "Sign-in accounts", "icon": "people"},
        ),
    ]
)

AppMenu.append(
    MenuItem(
        name="legal-documents",
        url=reverse_lazy("mvp_compliance:document", args=["privacy-policy"]),
        extra_context={"label": "Legal documents", "icon": "file-earmark-text"},
    )
)
