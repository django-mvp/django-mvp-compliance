"""The form a compliance editor uses to write a version."""

from django import forms

from mvp_compliance.models import Version
from mvp_compliance.widgets import MarkdownEditorWidget


class VersionForm(forms.ModelForm):
    """Everything a compliance editor may supply for a version.

    ``Meta.fields`` is an explicit allow list (FR-005): ``html`` is evidence
    ``Version.publish()`` produces (Article XIII) and is never postable, and
    ``number``, ``status`` and ``published_at`` are already ``editable=False``
    on the model.
    """

    class Meta:
        model = Version
        fields = ["document", "markdown"]
        widgets = {"markdown": MarkdownEditorWidget}
