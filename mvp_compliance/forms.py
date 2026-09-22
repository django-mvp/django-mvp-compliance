"""The form a compliance editor uses to write a version."""

from typing import cast

from django import forms
from django.utils.translation import gettext_lazy as _

from mvp_compliance.models import Version
from mvp_compliance.widgets import MarkdownEditorWidget


def same_wording(submitted: str, stored: str) -> bool:
    """Whether two wordings say the same thing.

    Neither difference this ignores is a difference a reader would see,
    and both of them are produced by the journey from a stored row to a
    form and back rather than by anybody editing anything.

    A browser submits a text area's content with carriage returns before
    every newline, which the value it was filled from does not have. And
    Django's ``CharField`` strips leading and trailing whitespace from
    what is submitted, while the stored wording keeps the trailing newline
    almost every document ends with.

    Compared without accounting for either, a wording resubmitted
    completely untouched never equals the one it came from, which is how
    this rule shipped refusing nothing at all.
    """
    return (
        submitted.replace("\r\n", "\n").strip() == stored.replace("\r\n", "\n").strip()
    )


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

    def clean(self) -> dict:
        """Refuse a new version that says exactly what the one in force says.

        The comparison is against the document's current version, read
        here from the document that was submitted — never against
        ``self.initial``. Django builds a bound form as
        ``ModelForm(request.POST, instance=obj)`` and passes no initial
        data on a post, so a form that compared against what it was seeded
        with would have nothing to compare against at exactly the moment
        it matters, and would refuse nothing.

        Only on an add. Re-saving an existing draft untouched is a
        different thing and is not refused. A document that has published
        nothing has no version in force, so its first version is never
        refused either.
        """
        cleaned = cast(dict, super().clean())
        document = cleaned.get("document")
        markdown = cleaned.get("markdown")
        if self.instance.pk is None and document is not None and markdown is not None:
            current = document.current
            if current is not None and same_wording(markdown, current.markdown):
                self.add_error(
                    "markdown",
                    forms.ValidationError(
                        _("This says exactly what the version in force already says.")
                    ),
                )
        return cleaned
