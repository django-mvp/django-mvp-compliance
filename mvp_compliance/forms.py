"""The forms this package's admin pages use."""

from typing import cast

from django import forms
from django.utils.translation import gettext_lazy as _

from mvp_compliance.models import Translation, Version, offered_languages
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
        fields = ["document", "markdown", "summary"]
        widgets = {"markdown": MarkdownEditorWidget}


class TranslationForm(forms.ModelForm):
    """Everything a translator may supply for a wording of a version.

    ``version`` and ``language`` are hidden fields on the add form, carried
    over from the address that opened it, and are absent on the change form,
    where they are shown read-only. The languages are read when the form is
    built, so a change to the site's ``LANGUAGES`` takes effect on the next
    request. The summary is only asked for when the version has one to
    translate.
    """

    language = forms.ChoiceField(label=_("language"), widget=forms.HiddenInput)

    class Meta:
        model = Translation
        fields = ["version", "language", "markdown", "summary"]
        widgets = {
            "version": forms.HiddenInput,
            "markdown": MarkdownEditorWidget,
        }

    def __init__(self, *args, **kwargs):
        """Fill the language choices and drop what does not apply to the version."""
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields.pop("language", None)
            self.fields.pop("version", None)
        else:
            self.fields["language"].choices = offered_languages()
            self.fields["version"].queryset = Version.objects.exclude(
                status=Version.Status.DRAFT
            )
        version = self.version()
        if version is not None and not version.summary.strip():
            self.fields.pop("summary", None)

    def version(self) -> "Version | None":
        """Find the version this form is about.

        Returns:
            The version of the instance, or the one the posted data or the
            initial data names. ``None`` when none is named or the value
            names no version.
        """
        if self.instance.pk:
            return cast(Version, self.instance.version)
        raw = self.data.get(self.add_prefix("version")) if self.is_bound else None
        raw = raw or self.initial.get("version")
        if isinstance(raw, Version):
            return raw
        if not raw:
            return None
        try:
            found: Version | None = Version.objects.filter(pk=raw).first()
        except (ValueError, TypeError):
            return None
        return found


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
