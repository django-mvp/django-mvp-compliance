"""VersionForm: what a compliance editor may supply for a version."""

import pytest

from mvp_compliance.widgets import MarkdownEditorWidget
from tests.factories import VersionFactory


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


@pytest.mark.django_db
class TestVersionFormRefusesUnchangedWording:
    """T060: a next version identical to the one in force changes nothing.

    ``VersionForm`` never knows on its own which version a form "started
    from" — the admin hands that over as ``initial``, the same way it does
    for FR-021's next-version wording. These tests supply ``initial`` the
    way the admin does, without going through a live request.
    """

    def test_refuses_a_save_identical_to_the_version_the_form_started_from(
        self, document
    ) -> None:
        from mvp_compliance.forms import VersionForm

        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()

        form = VersionForm(
            data={"document": document.pk, "markdown": current.markdown},
            initial={"document": document.pk, "markdown": current.markdown},
        )

        assert not form.is_valid()
        assert "markdown" in form.errors

    def test_a_changed_wording_saves(self, document) -> None:
        from mvp_compliance.forms import VersionForm

        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()

        form = VersionForm(
            data={"document": document.pk, "markdown": "The current wording, revised"},
            initial={"document": document.pk, "markdown": current.markdown},
        )

        assert form.is_valid(), form.errors
        version = form.save()

        assert version.markdown == "The current wording, revised"

    def test_the_first_version_of_a_document_is_never_refused(self, document) -> None:
        """Nothing published yet, so there is nothing to compare against."""
        from mvp_compliance.forms import VersionForm

        form = VersionForm(data={"document": document.pk, "markdown": "First wording"})

        assert form.is_valid(), form.errors

    def test_saving_an_existing_draft_unchanged_is_not_refused(self, document) -> None:
        """A change form's own initial is the instance's own wording, not the
        document's version in force — resaving a draft untouched is not the
        scenario this refusal guards against.
        """
        from mvp_compliance.forms import VersionForm

        draft = VersionFactory(document=document, markdown="Unpublished wording")

        form = VersionForm(
            data={"document": document.pk, "markdown": draft.markdown},
            initial={"document": document.pk, "markdown": draft.markdown},
            instance=draft,
        )

        assert form.is_valid(), form.errors
