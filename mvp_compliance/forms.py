"""The forms this package's admin pages use."""

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


class DisclosureForm(forms.Form):
    """Names who to produce everything held about (plan.md Design -> Naming a person).

    Free text rather than a picker: a removed account has no row left to
    choose, so the only way to ask about that person is the identifier
    their records still carry (research.md R3). Not bound to a model —
    ``Disclosure`` carries no fields of its own to post.
    """

    subject = forms.CharField(
        required=False,
        label=_("Person"),
        help_text=_(
            "The account's login name or email address, or, for somebody "
            "whose account has since been removed, the identifier their "
            "records still carry."
        ),
    )
