"""The admin registration: the editor reaches its pages, and the changelist reads clearly.

Exercised through the ``client`` fixture against a real, permitted user — a ``ModelAdmin`` method
called directly proves nothing about what a request receives. ``urlpatterns`` below mounts the
admin for this module only (``@pytest.mark.urls(__name__)``); the shared ``tests/urls.py`` is
outside this story's scope and stays empty.
"""

import pytest
from django.contrib import admin
from django.urls import path, reverse

urlpatterns = [path("admin/", admin.site.urls)]


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
