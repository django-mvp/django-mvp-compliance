"""Tests for mvp_compliance.views."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from mvp_compliance.rendering import MarkdownRenderer
from tests.factories import DocumentFactory, VersionFactory


def published(document, markdown="Wording"):
    """Publish a new version of ``document`` and return it."""
    version = VersionFactory(document=document, markdown=markdown)
    version.publish()
    return version


@pytest.mark.django_db
class TestDocumentView:
    """A visitor reads the version in force at an address that never changes."""

    def test_anonymous_visitor_reads_the_stored_html_byte_for_byte(self, client):
        document = DocumentFactory(slug="privacy-policy")
        version = published(document, "Some **bold** wording")

        response = client.get(reverse("mvp_compliance:document", args=[document.slug]))

        assert response.status_code == 200
        assert version.html in response.content.decode()

    def test_nothing_renders_markdown_while_the_page_is_served(self, client):
        document = DocumentFactory()
        version = published(document, "Some **bold** wording")

        with patch.object(
            MarkdownRenderer, "render", side_effect=AssertionError("rendered")
        ):
            response = client.get(
                reverse("mvp_compliance:document", args=[document.slug])
            )

        assert response.status_code == 200
        assert version.html in response.content.decode()

    def test_the_page_names_the_document_version_and_date_in_force(self, client):
        document = DocumentFactory(name="Privacy policy")
        version = published(document)

        response = client.get(reverse("mvp_compliance:document", args=[document.slug]))

        content = response.content.decode()
        assert "Privacy policy" in content
        assert f"Version {version.number}" in content
        assert date_format(timezone.localdate(version.published_at)) in content

    def test_the_breadcrumb_trail_is_the_title_with_no_empty_link(self, client):
        document = DocumentFactory(name="Privacy policy")
        published(document)

        response = client.get(reverse("mvp_compliance:document", args=[document.slug]))

        assert response.context["page"]["breadcrumbs"] == [{"text": "Privacy policy"}]

    def test_the_page_renders_in_the_shell_with_no_project_template(self, client):
        document = DocumentFactory()
        published(document)

        response = client.get(reverse("mvp_compliance:document", args=[document.slug]))

        names = [template.name for template in response.templates]
        assert names[0] == "mvp_compliance/document_detail.html"
        assert "page_view.html" in names
        assert "mvp/base.html" in names

    def test_a_later_publication_shows_at_the_same_address(self, client):
        document = DocumentFactory()
        published(document, "First wording")
        address = reverse("mvp_compliance:document", args=[document.slug])
        second = published(document, "Second wording")

        content = client.get(address).content.decode()

        assert second.html in content
        assert "First wording" not in content
        assert f"Version {second.number}" in content
