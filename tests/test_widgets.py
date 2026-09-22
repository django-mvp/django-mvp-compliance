"""The editor widget's declared toolbar and what it puts on the page."""

import html
import json
import re

from django.utils.functional import Promise

from mvp_compliance.widgets import MarkdownEditorWidget


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
