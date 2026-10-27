"""The demo's navigation: the pages a visitor reads, as a host project would add them.

The documentation is the demo's main app, so its contents are the sidebar on every
page and the entry goes on the documentation's menu rather than on ``AppMenu``.
"""

from django.urls import reverse_lazy
from flex_menu import MenuItem

from demo.mounted import docs

docs.menu.append(
    MenuItem(
        name="legal-documents",
        url=reverse_lazy("mvp_compliance:document", args=["privacy-policy"]),
        extra_context={"label": "Legal documents", "icon": "file-earmark-text"},
    )
)
