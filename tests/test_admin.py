"""The admin registration: the editor reaches its pages, and the changelist reads clearly.

Exercised through the ``client`` fixture against a real, permitted user — a ``ModelAdmin`` method
called directly proves nothing about what a request receives. ``urlpatterns`` below mounts the
admin for this module only (``@pytest.mark.urls(__name__)``); the shared ``tests/urls.py`` is
outside this story's scope and stays empty.
"""

import pytest
from django.contrib import admin
from django.http import HttpResponseForbidden
from django.urls import path, reverse

from mvp_compliance.rendering import get_renderer
from mvp_compliance.widgets import MarkdownEditorWidget

urlpatterns = [path("admin/", admin.site.urls)]


def _refuse(request, exception):
    """A 403 response that renders nothing of the host shell's.

    The project's own 403 page extends the django-mvp shell, which this
    module's isolated urlconf carries no configuration for (no
    ``EASY_ICONS``, outside this story's scope) — this stands in so a
    refusal itself can be asserted on without that unrelated gap.
    """
    return HttpResponseForbidden("Forbidden")


handler403 = _refuse

#: Every address this feature serves that exists yet, and how to reach one
#: given a draft to address it with. The preview and publish addresses are
#: not built until US-3 and US-4, so they are not walked here (T020).
DRAFT_PRIVACY_ADDRESSES = {
    "version changelist": lambda draft: reverse(
        "admin:mvp_compliance_version_changelist"
    ),
    "version add": lambda draft: reverse("admin:mvp_compliance_version_add"),
    "version change": lambda draft: reverse(
        "admin:mvp_compliance_version_change", args=[draft.pk]
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
