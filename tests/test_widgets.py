"""The editor widget's declared toolbar and what it puts on the page."""

import html
import json
import re
from pathlib import Path

from django.apps import apps
from django.utils.functional import Promise

from mvp_compliance.widgets import MarkdownEditorWidget

STATIC_DIR = (
    Path(apps.get_app_config("mvp_compliance").path) / "static" / "mvp_compliance"
)


class TestMarkdownEditorWidget:
    """FR-002, FR-003: the toolbar exists as data on the served markup."""

    def render(self) -> str:
        return MarkdownEditorWidget().render("markdown", "")

    def toolbar(self) -> list[dict]:
        rendered = self.render()
        match = re.search(r'data-toolbar="([^"]*)"', rendered)
        assert match, rendered
        return json.loads(html.unescape(match.group(1)))

    def test_it_carries_the_marker_attribute(self) -> None:
        assert "data-mvp-compliance-markdown-editor" in self.render()

    def test_the_declared_toolbar_is_exactly_these_seven_controls(self) -> None:
        names = [entry["name"] for entry in self.toolbar()]
        assert names == [
            "heading",
            "bold",
            "italic",
            "unordered-list",
            "ordered-list",
            "link",
            "quote",
        ]

    def test_it_offers_no_forbidden_control(self) -> None:
        """FR-003, US-1 scenario 2: no image, embed, table, tag or raw HTML."""
        names = {entry["name"] for entry in self.toolbar()}
        forbidden = {
            "image",
            "upload-image",
            "embed",
            "table",
            "tag",
            "raw-html",
            "code",
            "code-block",
        }
        assert names.isdisjoint(forbidden)

    def test_every_toolbar_label_is_translatable(self) -> None:
        for _name, label in MarkdownEditorWidget.TOOLBAR:
            assert isinstance(label, Promise)

    def test_media_orders_the_vendored_files_before_our_own(self) -> None:
        media = str(MarkdownEditorWidget().media)
        vendor_css = media.index("vendor/easymde/easymde.min.css")
        own_css = media.index("markdown-editor.css")
        vendor_js = media.index("vendor/easymde/easymde.min.js")
        own_js = media.index("markdown-editor.js")
        assert vendor_css < own_css
        assert vendor_js < own_js


class TestMarkdownEditorStaticAssets:
    """T013/T014: the script and stylesheet stay in step with the declared toolbar.

    Neither file's browser behaviour is reachable from this suite — there is
    no JavaScript runtime here — so this only guards the one thing static
    analysis can: a control named in ``TOOLBAR`` has a matching entry in
    both files, so an addition to one without the other fails here rather
    than rendering as a blank, non-functional button.
    """

    def test_every_toolbar_control_has_a_css_icon_rule(self) -> None:
        css = (STATIC_DIR / "markdown-editor.css").read_text()
        for name, _label in MarkdownEditorWidget.TOOLBAR:
            assert f".mvp-compliance-toolbar-{name}" in css

    def test_every_toolbar_control_is_wired_in_the_script(self) -> None:
        js = (STATIC_DIR / "markdown-editor.js").read_text()
        for name, _label in MarkdownEditorWidget.TOOLBAR:
            assert name in js

    def test_the_script_never_wires_up_a_preview_toggle(self) -> None:
        """R6: the editor's own preview is never enabled — the preview is US-3."""
        js = (STATIC_DIR / "markdown-editor.js").read_text()
        for forbidden in ("togglePreview", "toggleSideBySide", "toggleFullScreen"):
            assert forbidden not in js
