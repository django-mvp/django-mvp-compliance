"""The demo project's app."""

from django.apps import AppConfig


class DemoConfig(AppConfig):
    """Connects the demo's receivers when the project starts."""

    name = "demo"

    def ready(self):
        """Connect the receiver that emails the site's users about a new version."""
        from demo import receivers  # noqa: F401
