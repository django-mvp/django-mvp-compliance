"""Tests for mvp_compliance.rendering."""

from django.test import override_settings

from mvp_compliance.rendering import MarkdownRenderer, get_renderer


class TestMarkdownRenderer:
    """Renders authored Markdown, sanitised through an explicit allow list."""

    def test_safe_markup_survives_and_dangerous_markup_does_not(self):
        source = (
            "# Heading\n\n"
            "Some *emphasis* and **strong** text.\n\n"
            "- one\n- two\n\n"
            "[a link](https://example.com)\n\n"
            "| A | B |\n"
            "| --- | --- |\n"
            "| 1 | 2 |\n\n"
            '<script>alert("xss")</script>\n\n'
            "<style>body { display: none; }</style>\n\n"
            '<iframe src="https://evil.example.com"></iframe>\n\n'
            '<p onclick="alert(1)">click me</p>\n\n'
            "[bad link](javascript:alert(1))\n"
        )

        html = MarkdownRenderer().render(source)

        assert "<h1>Heading</h1>" in html
        assert "<em>emphasis</em>" in html
        assert "<strong>strong</strong>" in html
        assert "<li>one</li>" in html
        assert "<li>two</li>" in html
        assert '<a href="https://example.com">a link</a>' in html
        assert "<table>" in html
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html

        assert "<script" in source
        assert "<script" not in html
        assert "<style" in source
        assert "<style" not in html
        assert "<iframe" in source
        assert "<iframe" not in html
        assert "onclick" in source
        assert "onclick" not in html
        assert "javascript:" in source
        assert "javascript:" not in html

    def test_a_link_cannot_open_a_new_browsing_context(self):
        """What makes dropping ``rel`` safe (D19).

        ``rel="noopener noreferrer"`` only protects a link that opens a new
        browsing context, and ``target`` is not an attribute this renderer
        allows. Widen the allow list to include it and this fails, which is
        the point at which ``link_rel`` has to come back.
        """
        source = '<a href="https://example.com" target="_blank">a link</a>'

        html = MarkdownRenderer().render(source)

        assert "target" in source
        assert "target" not in html
        assert '<a href="https://example.com">a link</a>' in html

    def test_direction_overriding_characters_do_not_survive(self):
        """A link's visible text must not be able to disagree with its target.

        A right-to-left override reverses the text after it, so the wording a
        reader sees can be made to name a different site from the one the
        link points at. The allow list governs tags and attributes, not text,
        so this is removed separately.
        """
        source = "[https://good‮gro.example.com](https://evil.example.com)"

        html = MarkdownRenderer().render(source)

        assert "‮" in source
        assert "‮" not in html
        assert 'href="https://evil.example.com"' in html

    def test_invisible_characters_do_not_survive(self):
        """Two words separated by nothing a reader can see are one word."""
        source = "pay​pal.example.com is not pay﻿pal.example.com"

        html = MarkdownRenderer().render(source)

        assert "​" in source
        assert "​" not in html
        assert "﻿" not in html
        assert "paypal.example.com is not paypal.example.com" in html


class TestRendererSetting:
    """The renderer is resolved from a setting, defaulting to MarkdownRenderer."""

    def test_get_renderer_defaults_to_markdown_renderer(self):
        assert get_renderer() is MarkdownRenderer

    @override_settings(MVP_COMPLIANCE_RENDERER="tests.test_rendering.UppercaseRenderer")
    def test_get_renderer_resolves_a_configured_dotted_path(self):
        assert get_renderer() is UppercaseRenderer


class UppercaseRenderer(MarkdownRenderer):
    """A stand-in renderer that produces visibly different output."""

    def render(self, source: str) -> str:
        return super().render(source).upper()
