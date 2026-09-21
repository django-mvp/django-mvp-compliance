"""Turns authored Markdown into the HTML a reader is served.

Article XIII: this runs once, at publication (`Version.publish()`), and never
again on the way a stored version is read. A markup library upgrade or a
change to the allow list below cannot retroactively alter what a document
said when someone agreed to it.
"""

import markdown
import nh3


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

    def render(self, source: str) -> str:
        html = markdown.markdown(source, extensions=self.extensions)
        return nh3.clean(
            html,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            url_schemes=self.allowed_url_schemes,
            link_rel=None,
        )
