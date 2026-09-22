"""The form a compliance editor uses to write a version."""

from typing import cast

from django import forms
from django.utils.translation import gettext_lazy as _

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

    def clean_markdown(self) -> str:
        """Refuse a new version that says exactly what it started from.

        Only on an add: ``self.initial`` there carries the wording of the
        document's version in force (FR-021), never this form's own
        instance, so a change form re-saving an untouched draft is not
        this. A document that has published nothing leaves nothing in
        ``initial`` to compare against, so its first version is never
        refused (FR-022).
        """
        markdown = cast(str, self.cleaned_data["markdown"])
        if self.instance.pk is None:
            started_from = self.initial.get("markdown")
            if started_from and markdown == started_from:
                raise forms.ValidationError(
                    _("This says exactly what the version in force already says.")
                )
        return markdown
