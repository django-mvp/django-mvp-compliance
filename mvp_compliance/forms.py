"""The forms this package's admin pages use."""

from django import forms
from django.utils.translation import gettext_lazy as _

from mvp_compliance.models import Version
from mvp_compliance.widgets import MarkdownEditorWidget


class VersionForm(forms.ModelForm):
    """Everything a compliance editor may supply for a version.

    ``Meta.fields`` is an explicit allow list: ``html`` is evidence
    ``Version.publish()`` produces (Article XII) and is never postable, and
    ``number``, ``status`` and ``published_at`` are already ``editable=False``
    on the model.
    """

    class Meta:
        model = Version
        fields = ["document", "markdown"]
        widgets = {"markdown": MarkdownEditorWidget}


class DisclosureForm(forms.Form):
    """Names who to produce everything held about.

    Free text rather than a picker: a removed account has no row left to
    choose, so the only way to ask about that person is the identifier their
    records still carry. Not bound to a model, because ``Disclosure`` carries
    no fields of its own to post.
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


class ConfirmIdentityForm(forms.Form):
    """SKETCH (FS-012): the person's password, asked again before a copy is made."""

    password = forms.CharField(
        label=_("Your password"),
        help_text=_(
            "Asked again so that nobody else using this browser can download your data."
        ),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(
                _("That password is not right. Try again."), code="wrong_password"
            )
        return password
