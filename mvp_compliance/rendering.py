"""Turns authored Markdown into the HTML a reader is served.

Article XIII: this runs once, at publication (`Version.publish()`), and never
again on the way a stored version is read. A markup library upgrade or a
change to the allow list below cannot retroactively alter what a document
said when someone agreed to it.
"""

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

    #: Characters that change what text says without being visible in it.
    #: The allow list above governs tags, attributes and URL schemes, none of
    #: which reaches text content, so these are removed separately. The first
    #: group reorders the characters after it, which lets a link's wording
    #: name a different site from the one it points at. The second is
    #: invisible, which lets two words read as one.
    discarded_characters = str.maketrans(
        "",
        "",
        "‪‫‬‭‮⁦⁧⁨⁩​‌‍‎‏﻿",
    )

    def render(self, source: str) -> str:
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
    """Resolve the renderer class, defaulting to :class:`MarkdownRenderer`.

    A host project points ``MVP_COMPLIANCE_RENDERER`` at a dotted path to
    override it.
    """
    dotted_path = getattr(settings, "MVP_COMPLIANCE_RENDERER", None)
    if dotted_path is None:
        return MarkdownRenderer
    return cast(type[MarkdownRenderer], import_string(dotted_path))
