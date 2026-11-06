"""VersionForm: what a compliance editor may supply for a version."""

import pytest
from django.test import override_settings

from mvp_compliance.widgets import MarkdownEditorWidget


class TestVersionForm:
    def test_the_markdown_field_uses_the_editor_widget(self) -> None:
        from mvp_compliance.forms import VersionForm

        assert isinstance(VersionForm().fields["markdown"].widget, MarkdownEditorWidget)

    def test_it_exposes_only_what_an_author_supplies(self) -> None:
        from mvp_compliance.forms import VersionForm

        assert list(VersionForm().fields) == ["document", "markdown", "summary"]

    @pytest.mark.django_db
    def test_markdown_typed_by_hand_round_trips_unchanged(self, document) -> None:
        from mvp_compliance.forms import VersionForm

        source = (
            "# Heading\n\nSome *text* with a [link](https://example.com).\n\n> Quoted."
        )
        form = VersionForm(data={"document": document.pk, "markdown": source})

        assert form.is_valid(), form.errors
        version = form.save()

        assert version.markdown == source


@pytest.mark.django_db
class TestTranslationForm:
    def test_language_choices_come_from_the_languages_offered_when_it_is_built(
        self, site_languages
    ) -> None:
        from mvp_compliance.forms import TranslationForm
        from mvp_compliance.models import offered_languages
        from tests.factories import VersionFactory

        version = VersionFactory(pending=True)

        with_three = TranslationForm(initial={"version": version.pk})
        with override_settings(LANGUAGES=[("en", "English"), ("it", "Italian")]):
            with_italian = TranslationForm(initial={"version": version.pk})

        assert list(with_three.fields["language"].choices) == offered_languages()
        assert [code for code, _name in with_three.fields["language"].choices] == [
            "de",
            "fr",
        ]
        assert [code for code, _name in with_italian.fields["language"].choices] == [
            "it"
        ]

    def test_a_language_the_site_does_not_offer_is_refused(
        self, site_languages
    ) -> None:
        from mvp_compliance.forms import TranslationForm
        from tests.factories import VersionFactory

        version = VersionFactory(pending=True)

        form = TranslationForm(
            data={"version": version.pk, "language": "en", "markdown": "Text"}
        )

        assert not form.is_valid()
        assert "language" in form.errors

    def test_a_draft_version_is_refused(self, site_languages, draft) -> None:
        from mvp_compliance.forms import TranslationForm

        form = TranslationForm(
            data={"version": draft.pk, "language": "de", "markdown": "Text"}
        )

        assert not form.is_valid()
        assert "version" in form.errors

    def test_the_summary_field_is_absent_when_the_version_has_none(
        self, site_languages
    ) -> None:
        from mvp_compliance.forms import TranslationForm
        from tests.factories import VersionFactory

        without = VersionFactory(pending=True, summary="")
        with_summary = VersionFactory(pending=True, summary="What changed")

        assert "summary" not in TranslationForm(initial={"version": without.pk}).fields
        assert "summary" in TranslationForm(initial={"version": with_summary.pk}).fields

    def test_the_markdown_field_uses_the_editor_widget(self, site_languages) -> None:
        from mvp_compliance.forms import TranslationForm

        assert isinstance(
            TranslationForm().fields["markdown"].widget, MarkdownEditorWidget
        )
