"""Turns authored Markdown into the HTML a reader is served, once, at publication."""

from typing import cast

import markdown
import nh3
from django.conf import settings
from django.utils.module_loading import import_string


class MarkdownRenderer:
    """Renders Markdown to HTML, then sanitises it against an explicit allow list.

    A host project that wants a different allow list subclasses this and
    points ``MVP_COMPLIANCE_RENDERER`` at the subclass.
    """

    extensions = ["extra", "sane_lists", "smarty"]

    allowed_tags = {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "ul",
        "ol",
        "li",
        "em",
        "strong",
        "a",
        "blockquote",
        "code",
        "pre",
        "hr",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    }

    allowed_attributes = {
        "a": {"href", "title"},
        "th": {"colspan", "rowspan"},
        "td": {"colspan", "rowspan"},
    }

    allowed_url_schemes = {"http", "https", "mailto"}

    #: Characters that change what text says without being visible in it, which
    #: the allow list cannot reach. The first group reorders the text after it,
    #: so a link's wording can name another site. The second is invisible.
    discarded_characters = str.maketrans(
        "",
        "",
        "‪‫‬‭‮⁦⁧⁨⁩​‌‍‎‏﻿",
    )

    def render(self, source: str) -> str:
        """Render Markdown to sanitised HTML.

        Args:
            source: The authored Markdown.

        Returns:
            HTML holding only the allowed tags, attributes and URL schemes.
        """
        html = markdown.markdown(
            source.translate(self.discarded_characters), extensions=self.extensions
        )
        return nh3.clean(
            html,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            url_schemes=self.allowed_url_schemes,
            link_rel=None,
        )


def get_renderer() -> type[MarkdownRenderer]:
    """Resolve the renderer class.

    A host project points ``MVP_COMPLIANCE_RENDERER`` at a dotted path to
    override it.

    Returns:
        The configured class, or :class:`MarkdownRenderer` by default.
    """
    dotted_path = getattr(settings, "MVP_COMPLIANCE_RENDERER", None)
    if dotted_path is None:
        return MarkdownRenderer
    return cast(type[MarkdownRenderer], import_string(dotted_path))
