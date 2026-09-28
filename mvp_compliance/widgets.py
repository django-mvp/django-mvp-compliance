"""The Markdown editor widget the authoring surface renders."""

import json

from django import forms
from django.utils.translation import gettext_lazy as _


class MarkdownEditorWidget(forms.Textarea):
    """A ``Textarea`` that becomes a formatting-control editor in the browser.

    The toolbar is declared here as data: a fixed set of controls,
    serialised onto the rendered element as ``data-toolbar``, and
    ``markdown-editor.js`` builds EasyMDE from exactly that list. Nothing the
    editor can produce exists outside this declaration.
    """

    #: (name, label) pairs, in toolbar order. Names are EasyMDE's own built-in
    #: action names, so ``markdown-editor.js`` hands each straight to the library.
    TOOLBAR = [
        ("heading", _("Heading")),
        ("bold", _("Bold")),
        ("italic", _("Italic")),
        ("unordered-list", _("Bulleted list")),
        ("ordered-list", _("Numbered list")),
        ("link", _("Link")),
        ("quote", _("Quote")),
    ]

    class Media:
        css = {
            "all": (
                "mvp_compliance/vendor/easymde/easymde.min.css",
                "mvp_compliance/markdown-editor.css",
            )
        }
        js = (
            "mvp_compliance/vendor/easymde/easymde.min.js",
            "mvp_compliance/markdown-editor.js",
        )

    def get_context(self, name: str, value, attrs) -> dict:
        """Add the marker attribute and the serialised toolbar."""
        context = super().get_context(name, value, attrs)
        widget_attrs = context["widget"]["attrs"]
        widget_attrs["data-mvp-compliance-markdown-editor"] = True
        widget_attrs["data-toolbar"] = json.dumps(
            [{"name": name, "title": str(label)} for name, label in self.TOOLBAR]
        )
        return context
