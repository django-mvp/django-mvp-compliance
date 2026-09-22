"""VersionForm: what a compliance editor may supply for a version."""

import pytest

from mvp_compliance.widgets import MarkdownEditorWidget


class TestVersionForm:
    """FR-005: stored content is ordinary Markdown, unmodified either way."""

    def test_the_markdown_field_uses_the_editor_widget(self) -> None:
        from mvp_compliance.forms import VersionForm

        assert isinstance(VersionForm().fields["markdown"].widget, MarkdownEditorWidget)

    def test_it_exposes_only_what_an_author_supplies(self) -> None:
        """FR-005: html is publish()'s own evidence and is never postable."""
        from mvp_compliance.forms import VersionForm

        assert list(VersionForm().fields) == ["document", "markdown"]

    @pytest.mark.django_db
    def test_markdown_typed_by_hand_round_trips_unchanged(self, document) -> None:
        """US-1 scenario 3: an author who knows Markdown is not obstructed."""
        from mvp_compliance.forms import VersionForm

        source = (
            "# Heading\n\nSome *text* with a [link](https://example.com).\n\n> Quoted."
        )
        form = VersionForm(data={"document": document.pk, "markdown": source})

        assert form.is_valid(), form.errors
        version = form.save()

        assert version.markdown == source
