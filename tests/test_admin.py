"""The admin registration: the editor reaches its pages, and the changelist reads clearly.

Exercised through the ``client`` fixture against a real, permitted user — a ``ModelAdmin`` method
called directly proves nothing about what a request receives. ``urlpatterns`` below mounts the
admin for this module only (``@pytest.mark.urls(__name__)``); the shared ``tests/urls.py`` stays
empty because this package serves no address of its own.
"""

import pytest
from django.contrib import admin
from django.test import override_settings
from django.urls import path, reverse

from mvp_compliance.models import Version
from mvp_compliance.rendering import get_renderer
from mvp_compliance.widgets import MarkdownEditorWidget
from tests.factories import VersionFactory

urlpatterns = [path("admin/", admin.site.urls)]

#: Every address this feature serves that exists yet, and how to reach one
#: given a draft to address it with. The publish address is not built until
#: US-4, so it is not walked here (T020).
DRAFT_PRIVACY_ADDRESSES = {
    "version changelist": lambda draft: reverse(
        "admin:mvp_compliance_version_changelist"
    ),
    "version add": lambda draft: reverse("admin:mvp_compliance_version_add"),
    "version change": lambda draft: reverse(
        "admin:mvp_compliance_version_change", args=[draft.pk]
    ),
    "version preview": lambda draft: reverse(
        "admin:mvp_compliance_version_preview", args=[draft.pk]
    ),
    "document changelist": lambda draft: reverse(
        "admin:mvp_compliance_document_changelist"
    ),
    "document change": lambda draft: reverse(
        "admin:mvp_compliance_document_change", args=[draft.document_id]
    ),
}

#: One Markdown sample per toolbar control and the tag its output must
#: survive as. A control added to ``MarkdownEditorWidget.TOOLBAR`` without a
#: matching entry here fails ``test_every_toolbar_control_survives_publication``
#: with a ``KeyError`` rather than being silently skipped (T018).
TOOLBAR_SAMPLES = {
    "heading": ("# Heading", "<h1>"),
    "bold": ("**bold**", "<strong>"),
    "italic": ("*italic*", "<em>"),
    "unordered-list": ("- item", "<ul>"),
    "ordered-list": ("1. item", "<ol>"),
    "link": ("[text](https://example.com)", "<a "),
    "quote": ("> quoted", "<blockquote>"),
}


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestVersionAdmin:
    """T017: the editor reaches the add and change pages and finds the editor markup."""

    def test_the_add_page_carries_the_editor_widget(self, client, editor) -> None:
        client.force_login(editor)

        response = client.get(reverse("admin:mvp_compliance_version_add"))

        assert response.status_code == 200
        assert b"data-mvp-compliance-markdown-editor" in response.content

    def test_the_change_page_carries_the_editor_widget_for_a_draft(
        self, client, editor, draft
    ) -> None:
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk])
        )

        assert response.status_code == 200
        assert b"data-mvp-compliance-markdown-editor" in response.content

    def test_the_changelist_shows_document_number_status_and_published_time(
        self, client, editor, published_version
    ) -> None:
        client.force_login(editor)

        response = client.get(reverse("admin:mvp_compliance_version_changelist"))

        assert response.status_code == 200
        content = response.content.decode()
        assert str(published_version.document) in content
        assert str(published_version.number) in content
        assert "Current" in content


class TestToolbarAgreesWithTheAllowList:
    """FR-004, SC-002, US-1 scenario 4: the toolbar and the allow list agree.

    Fails in both directions: a control whose output publication would strip
    cannot be added without this test saying so, and content the allow list
    is meant to remove has to actually be removed.
    """

    def test_every_toolbar_control_survives_publication(self) -> None:
        renderer = get_renderer()()
        for name, _label in MarkdownEditorWidget.TOOLBAR:
            markdown_sample, expected_tag = TOOLBAR_SAMPLES[name]
            html = renderer.render(markdown_sample)
            assert expected_tag in html, (
                f"{name!r} control's output was stripped: {html!r}"
            )

    def test_content_the_allow_list_strips_is_stripped(self) -> None:
        html = get_renderer()().render("<script>alert('x')</script>")
        assert "<script" not in html


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestDraftPrivacy:
    """FR-006 to FR-009, SC-003, US-2 scenarios 1-5: a draft belongs to its
    author until it is published — nothing about it is reachable, at any
    address this package serves, by anybody lacking the permission to work
    on documents.
    """

    @pytest.mark.parametrize("address", DRAFT_PRIVACY_ADDRESSES)
    def test_anonymous_reaches_nothing(self, client, draft, address) -> None:
        response = client.get(DRAFT_PRIVACY_ADDRESSES[address](draft))

        assert response.status_code == 302
        assert draft.markdown.encode() not in response.content

    @pytest.mark.parametrize("address", DRAFT_PRIVACY_ADDRESSES)
    def test_a_signed_in_non_staff_visitor_reaches_nothing(
        self, client, visitor, draft, address
    ) -> None:
        client.force_login(visitor)

        response = client.get(DRAFT_PRIVACY_ADDRESSES[address](draft))

        assert response.status_code == 302
        assert draft.markdown.encode() not in response.content

    @pytest.mark.parametrize("address", DRAFT_PRIVACY_ADDRESSES)
    def test_staff_without_permissions_reaches_nothing(
        self, client, staff_without_permissions, draft, address
    ) -> None:
        client.force_login(staff_without_permissions)

        response = client.get(DRAFT_PRIVACY_ADDRESSES[address](draft))

        assert response.status_code == 403
        assert draft.markdown.encode() not in response.content

    def test_a_published_version_offers_no_delete_action(
        self, client, editor, published_version
    ) -> None:
        """T021: the admin offers nothing that ``Version.delete()`` would refuse."""
        client.force_login(editor)
        change_url = reverse(
            "admin:mvp_compliance_version_change", args=[published_version.pk]
        )
        delete_url = reverse(
            "admin:mvp_compliance_version_delete", args=[published_version.pk]
        )

        change_response = client.get(change_url)
        delete_response = client.get(delete_url)

        assert delete_url.encode() not in change_response.content
        assert delete_response.status_code == 403

    def test_a_draft_survives_being_left_alone(self, client, editor, draft) -> None:
        """T022, US-2 scenario 1, FR-006: fetched and saved again, unchanged."""
        client.force_login(editor)
        original_markdown = draft.markdown
        change_url = reverse("admin:mvp_compliance_version_change", args=[draft.pk])

        get_response = client.get(change_url)
        post_response = client.post(
            change_url,
            data={"document": draft.document_id, "markdown": original_markdown},
        )

        draft.refresh_from_db()
        assert get_response.status_code == 200
        assert post_response.status_code == 302
        assert draft.markdown == original_markdown
        assert draft.status == draft.Status.DRAFT

    def test_discarding_a_draft_leaves_other_versions_alone(
        self, client, editor, document
    ) -> None:
        """T023, US-2 scenario 2: deleting one draft touches no other version."""
        client.force_login(editor)
        keeper = VersionFactory(document=document)
        keeper.publish()
        victim = VersionFactory(document=document)
        delete_url = reverse("admin:mvp_compliance_version_delete", args=[victim.pk])

        response = client.post(delete_url, data={"post": "yes"})

        assert response.status_code == 302
        assert not Version.objects.filter(pk=victim.pk).exists()
        keeper.refresh_from_db()
        assert keeper.status == Version.Status.CURRENT

    def test_every_draft_of_a_document_is_listed_and_separately_editable(
        self, client, editor, document
    ) -> None:
        """T024, US-2 scenario 5, FR-009."""
        client.force_login(editor)
        drafts = [VersionFactory(document=document) for _ in range(3)]

        changelist_content = client.get(
            reverse("admin:mvp_compliance_version_changelist")
        ).content.decode()
        for version in drafts:
            assert str(version.number) in changelist_content

        for version in drafts:
            response = client.get(
                reverse("admin:mvp_compliance_version_change", args=[version.pk])
            )
            content = response.content.decode()
            others = [other for other in drafts if other.pk != version.pk]

            assert response.status_code == 200
            assert version.markdown in content
            assert all(other.markdown not in content for other in others)


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestPreview:
    """FR-010 to FR-012, SC-004, US-3 scenarios 1-5: the preview is the
    rendering a reader will actually be served, not the editor's own
    approximation of it.
    """

    def test_editor_receives_the_rendering_of_the_drafts_markdown(
        self, client, editor, draft
    ) -> None:
        """T030, FR-010, US-3 scenario 1."""
        client.force_login(editor)
        expected_html = get_renderer()().render(draft.markdown)

        response = client.get(
            reverse("admin:mvp_compliance_version_preview", args=[draft.pk])
        )

        assert response.status_code == 200
        assert expected_html in response.content.decode()

    def test_a_published_versions_preview_reads_the_stored_html_not_a_fresh_rendering(
        self, client, editor, published_version
    ) -> None:
        """T031, Article XIII: a published version's stored html is the
        evidence, and it is never produced again — even when the renderer
        that would produce it has since changed.
        """
        client.force_login(editor)
        stored_html = published_version.html

        with override_settings(
            MVP_COMPLIANCE_RENDERER="tests.test_models.UppercaseRenderer"
        ):
            response = client.get(
                reverse(
                    "admin:mvp_compliance_version_preview",
                    args=[published_version.pk],
                )
            )

        content = response.content.decode()
        assert response.status_code == 200
        assert stored_html in content
        assert stored_html.upper() not in content

    def test_the_preview_page_states_what_a_reader_will_be_served(
        self, client, editor, draft
    ) -> None:
        """T032, US-3 scenario 5: the distinction from the editor's inline
        display is on the page, not only in the specification.
        """
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_preview", args=[draft.pk])
        )

        assert response.status_code == 200
        assert b"This is what a reader will be served" in response.content

    def test_the_preview_links_back_to_the_version(self, client, editor, draft) -> None:
        """T032."""
        client.force_login(editor)
        change_url = reverse("admin:mvp_compliance_version_change", args=[draft.pk])

        response = client.get(
            reverse("admin:mvp_compliance_version_preview", args=[draft.pk])
        )

        assert response.status_code == 200
        assert change_url.encode() in response.content

    def test_the_preview_shows_stripped_content_as_stripped(
        self, client, editor, document
    ) -> None:
        """T033, FR-011, US-3 scenario 3, US-1 scenario 5: what the allow
        list removes is visibly gone before publication, not discovered
        after.
        """
        client.force_login(editor)
        version = VersionFactory(
            document=document,
            markdown="Safe wording\n\n<script>alert('mvp-compliance-preview-test')</script>",
        )

        response = client.get(
            reverse("admin:mvp_compliance_version_preview", args=[version.pk])
        )

        content = response.content.decode()
        assert response.status_code == 200
        assert "Safe wording" in content
        assert "mvp-compliance-preview-test" not in content
