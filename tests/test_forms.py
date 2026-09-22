"""VersionForm: what a compliance editor may supply for a version."""

import pytest
from django.contrib import admin
from django.urls import path, reverse

from mvp_compliance.widgets import MarkdownEditorWidget
from tests.factories import VersionFactory

urlpatterns = [path("admin/", admin.site.urls)]


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
@pytest.mark.urls(__name__)
class TestVersionFormRefusesUnchangedWording:
    """T060: a next version identical to the one in force changes nothing.

    Every test here goes through the admin's own add page, as a browser
    does. Building the form by hand and handing it ``initial`` proves
    nothing about this rule: Django builds a bound form as
    ``ModelForm(request.POST, instance=obj)`` and passes no initial data on
    a post, so a form that compared against what it was seeded with would
    refuse nothing at the only moment that counts. That is exactly what the
    first version of this shipped, and it passed its own tests while doing
    nothing at all in the browser.
    """

    def add_url(self, document):
        """The add page as the next-version control reaches it."""
        return f"{reverse('admin:mvp_compliance_version_add')}?document={document.pk}"

    def test_a_version_identical_to_the_one_in_force_is_refused(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()

        response = client.post(
            self.add_url(document),
            data={"document": document.pk, "markdown": current.markdown},
        )

        assert response.status_code == 200
        assert b"exactly what the version in force already says" in response.content
        assert document.versions.count() == 1

    def test_a_version_identical_but_for_how_a_browser_sends_it_is_refused(
        self, client, editor, document
    ) -> None:
        """The case the first two attempts at this rule both missed.

        The stored wording ends with a newline, as almost every document
        does, and Django strips that from what is submitted. A browser also
        sends a text area's content with a carriage return before every
        newline, which the value it was filled from does not have. Either
        difference alone is enough to make an untouched resubmission look
        like a change, and together they are why this refused nothing in a
        real browser while its own tests passed.
        """
        client.force_login(editor)
        current = VersionFactory(
            document=document, markdown="## Heading\n\nA clause.\n"
        )
        current.publish()

        response = client.post(
            self.add_url(document),
            data={
                "document": document.pk,
                "markdown": "## Heading\r\n\r\nA clause.",
            },
        )

        assert response.status_code == 200
        assert b"exactly what the version in force already says" in response.content
        assert document.versions.count() == 1

    def test_a_changed_wording_saves(self, client, editor, document) -> None:
        client.force_login(editor)
        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()

        response = client.post(
            self.add_url(document),
            data={
                "document": document.pk,
                "markdown": "The current wording, revised",
            },
        )

        assert response.status_code == 302
        assert document.versions.count() == 2
        assert document.versions.drafts().get().markdown == (
            "The current wording, revised"
        )

    def test_the_first_version_of_a_document_is_never_refused(
        self, client, editor, document
    ) -> None:
        """Nothing in force, so there is nothing it could be identical to."""
        client.force_login(editor)

        response = client.post(
            self.add_url(document),
            data={"document": document.pk, "markdown": "First wording"},
        )

        assert response.status_code == 302
        assert document.versions.get().markdown == "First wording"

    def test_a_version_identical_to_a_sibling_draft_is_not_refused(
        self, client, editor, document
    ) -> None:
        """The comparison is against the version in force, not against drafts.

        A draft has no standing, so a new version saying what an
        unpublished sibling says is not a version that changes nothing.
        """
        client.force_login(editor)
        VersionFactory(document=document, markdown="Unpublished wording")

        response = client.post(
            self.add_url(document),
            data={"document": document.pk, "markdown": "Unpublished wording"},
        )

        assert response.status_code == 302
        assert document.versions.count() == 2

    def test_saving_an_existing_draft_unchanged_is_not_refused(
        self, client, editor, document
    ) -> None:
        """Re-saving a draft you are still working on is not this rule."""
        client.force_login(editor)
        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()
        draft = VersionFactory(document=document, markdown="The current wording")

        response = client.post(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk]),
            data={"document": document.pk, "markdown": draft.markdown},
        )

        draft.refresh_from_db()
        assert response.status_code == 302
        assert draft.markdown == "The current wording"
