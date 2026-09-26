"""Tests for mvp_compliance.views."""

from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
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

    def test_the_page_links_to_the_versions_of_the_document(self, client):
        document = DocumentFactory(slug="privacy-policy")
        published(document)

        content = client.get(
            reverse("mvp_compliance:document", args=[document.slug])
        ).content.decode()

        address = reverse("mvp_compliance:versions", args=[document.slug])
        assert f'href="{address}"' in content
        assert "Earlier versions" in content

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

    def test_a_document_with_only_a_draft_is_not_found_for_everybody(
        self, client, django_user_model
    ):
        document = DocumentFactory()
        VersionFactory(document=document)
        address = reverse("mvp_compliance:document", args=[document.slug])
        signed_in = django_user_model.objects.create_user("reader", password="pw")
        staff = django_user_model.objects.create_user(
            "editor", password="pw", is_staff=True, is_superuser=True
        )

        assert client.get(address).status_code == 404
        client.force_login(signed_in)
        assert client.get(address).status_code == 404
        client.force_login(staff)
        assert client.get(address).status_code == 404

    def test_an_unknown_slug_is_not_found_for_everybody(
        self, client, django_user_model
    ):
        address = reverse("mvp_compliance:document", args=["no-such-document"])
        staff = django_user_model.objects.create_user(
            "editor", password="pw", is_staff=True, is_superuser=True
        )

        assert client.get(address).status_code == 404
        client.force_login(staff)
        assert client.get(address).status_code == 404

    def test_markup_in_a_document_name_is_escaped(self, client):
        document = DocumentFactory(name="<script>alert(1)</script>")
        published(document)

        content = client.get(
            reverse("mvp_compliance:document", args=[document.slug])
        ).content.decode()

        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content

    def test_the_query_count_does_not_grow_with_the_versions_published(
        self, client, django_assert_num_queries
    ):
        one = DocumentFactory()
        published(one)
        many = DocumentFactory()
        for n in range(5):
            published(many, f"Wording {n}")
        client.get(reverse("mvp_compliance:document", args=[one.slug]))  # warm caches

        with CaptureQueriesContext(connection) as single:
            client.get(reverse("mvp_compliance:document", args=[one.slug]))
        with django_assert_num_queries(len(single)):
            client.get(reverse("mvp_compliance:document", args=[many.slug]))

    def test_no_link_or_button_to_edit_or_delete_is_drawn(
        self, client, django_user_model
    ):
        document = DocumentFactory()
        published(document)
        staff = django_user_model.objects.create_user(
            "editor", password="pw", is_staff=True, is_superuser=True
        )
        client.force_login(staff)

        response = client.get(reverse("mvp_compliance:document", args=[document.slug]))

        assert response.context["directory"] == {}
        content = response.content.decode()
        assert "/change/" not in content
        assert "/delete/" not in content


def version_address(version):
    return reverse(
        "mvp_compliance:version", args=[version.document.slug, version.number]
    )


@pytest.mark.django_db
class TestVersionView:
    """A visitor reads any published version at its own permanent address."""

    def test_a_superseded_version_shows_its_stored_html_and_says_it_was_replaced(
        self, client
    ):
        document = DocumentFactory(slug="privacy-policy")
        first = published(document, "First **bold** wording")
        second = published(document, "Second wording")
        first.refresh_from_db()
        second.refresh_from_db()

        response = client.get(version_address(first))

        content = response.content.decode()
        assert response.status_code == 200
        assert first.html in content
        assert second.html not in content
        assert "replaced" in content
        assert date_format(timezone.localdate(first.published_at)) in content
        assert date_format(timezone.localdate(second.published_at)) in content
        assert reverse("mvp_compliance:document", args=[document.slug]) in content

    def test_the_current_version_says_it_is_in_force_as_the_document_page_does(
        self, client
    ):
        document = DocumentFactory()
        published(document, "First wording")
        current = published(document, "Second wording")
        current.refresh_from_db()

        document_page = client.get(
            reverse("mvp_compliance:document", args=[document.slug])
        ).content.decode()
        response = client.get(version_address(current))

        content = response.content.decode()
        assert response.status_code == 200
        assert current.html in content
        assert "in force" in content
        assert "replaced" not in content
        assert f"Version {current.number}, in force since" in document_page
        assert f"Version {current.number}, in force since" in content

    def test_a_later_publication_leaves_a_versions_address_and_wording_alone(
        self, client
    ):
        document = DocumentFactory()
        first = published(document, "First wording")
        address = version_address(first)
        before = client.get(address).content.decode()
        assert "replaced" not in before

        second = published(document, "Second wording")
        after = client.get(address)

        assert version_address(first) == address
        assert after.status_code == 200
        assert first.html in after.content.decode()
        assert second.html not in after.content.decode()
        assert "replaced" in after.content.decode()

    def test_a_number_belonging_to_another_document_is_not_found(self, client):
        mine = DocumentFactory(slug="mine")
        theirs = DocumentFactory(slug="theirs")
        published(mine)
        published(theirs, "First wording")
        other = published(theirs, "Second wording")

        response = client.get(
            reverse("mvp_compliance:version", args=["mine", other.number])
        )

        assert response.status_code == 404

    def test_a_number_that_was_never_published_is_not_found(self, client):
        document = DocumentFactory()
        published(document)

        response = client.get(
            reverse("mvp_compliance:version", args=[document.slug, "1999.1"])
        )

        assert response.status_code == 404

    def test_a_draft_is_unreachable_by_number_for_everybody(
        self, client, django_user_model
    ):
        document = DocumentFactory()
        first = published(document)
        draft = VersionFactory(document=document)
        staff = django_user_model.objects.create_user(
            "editor", password="pw", is_staff=True, is_superuser=True
        )
        client.force_login(staff)

        next_number = (
            f"{first.number.split('.')[0]}.{int(first.number.split('.')[1]) + 1}"
        )
        response = client.get(
            reverse("mvp_compliance:version", args=[document.slug, next_number])
        )

        assert draft.number is None
        assert response.status_code == 404

    def test_a_document_with_only_drafts_has_no_version_pages(self, client):
        document = DocumentFactory()
        VersionFactory(document=document)

        response = client.get(
            reverse("mvp_compliance:version", args=[document.slug, "2026.1"])
        )

        assert response.status_code == 404

    def test_the_page_renders_in_the_shell_and_reads_the_version_on_its_own(
        self, client
    ):
        document = DocumentFactory(name="Privacy policy")
        version = published(document)

        response = client.get(version_address(version))

        names = [template.name for template in response.templates]
        assert names[0] == "mvp_compliance/version_detail.html"
        assert "page_view.html" in names
        assert "mvp/base.html" in names
        content = response.content.decode()
        assert "Privacy policy" in content
        assert f"Version {version.number}" in content
        assert response.context["directory"] == {}

    def test_the_breadcrumb_trail_links_the_document_then_names_the_version(
        self, client
    ):
        document = DocumentFactory(name="Privacy policy")
        version = published(document)

        response = client.get(version_address(version))

        assert response.context["page"]["breadcrumbs"] == [
            {
                "text": "Privacy policy",
                "href": reverse("mvp_compliance:document", args=[document.slug]),
            },
            {"text": f"Version {version.number}"},
        ]

    def test_nothing_renders_markdown_while_the_page_is_served(self, client):
        document = DocumentFactory()
        version = published(document, "Some **bold** wording")

        with patch.object(
            MarkdownRenderer, "render", side_effect=AssertionError("rendered")
        ):
            response = client.get(version_address(version))

        assert response.status_code == 200
        assert version.html in response.content.decode()

    def test_markup_in_a_document_name_is_escaped(self, client):
        document = DocumentFactory(name="<script>alert(1)</script>")
        version = published(document)

        content = client.get(version_address(version)).content.decode()

        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content

    def test_the_query_count_does_not_grow_with_the_versions_published(
        self, client, django_assert_num_queries
    ):
        one = DocumentFactory()
        only = published(one)
        many = DocumentFactory()
        first = published(many)
        for n in range(5):
            published(many, f"Wording {n}")
        client.get(version_address(only))  # warm caches

        with CaptureQueriesContext(connection) as single:
            client.get(version_address(only))
        with django_assert_num_queries(len(single)):
            client.get(version_address(first))


@pytest.mark.django_db
class TestVersionListView:
    """A visitor finds every published version of a document, newest first."""

    def test_every_published_version_is_listed_newest_first_with_its_dates(
        self, client
    ):
        document = DocumentFactory(name="Privacy policy")
        first = published(document, "One")
        second = published(document, "Two")
        third = published(document, "Three")
        VersionFactory(document=document, markdown="Draft")

        response = client.get(reverse("mvp_compliance:versions", args=[document.slug]))

        assert response.status_code == 200
        assert list(response.context["versions"]) == [third, second, first]
        content = response.content.decode()
        for version in (first, second, third):
            assert f"{version.number}" in content
            assert f'href="{version_address(version)}"' in content
            assert date_format(timezone.localdate(version.published_at)) in content
        # the first version was replaced the day the second was published
        assert date_format(timezone.localdate(second.published_at)) in content

    def test_the_version_in_force_is_marked_and_the_others_are_not(self, client):
        document = DocumentFactory()
        published(document, "One")
        published(document, "Two")

        content = client.get(
            reverse("mvp_compliance:versions", args=[document.slug])
        ).content.decode()

        assert content.count("In force") == 1

    def test_no_draft_is_listed(self, client):
        document = DocumentFactory()
        published(document)
        draft = VersionFactory(document=document, markdown="Draft")

        response = client.get(reverse("mvp_compliance:versions", args=[document.slug]))

        assert draft not in list(response.context["versions"])
        assert len(response.context["versions"]) == 1

    def test_a_document_with_only_drafts_is_not_found(self, client):
        document = DocumentFactory()
        VersionFactory(document=document)

        response = client.get(reverse("mvp_compliance:versions", args=[document.slug]))

        assert response.status_code == 404

    def test_an_unknown_slug_is_not_found(self, client):
        response = client.get(reverse("mvp_compliance:versions", args=["nothing"]))

        assert response.status_code == 404

    def test_the_page_renders_in_the_shell_with_the_title_of_the_document(
        self, client
    ):
        document = DocumentFactory(name="Privacy policy")
        published(document)

        response = client.get(reverse("mvp_compliance:versions", args=[document.slug]))

        names = [template.name for template in response.templates]
        assert names[0] == "mvp_compliance/version_list.html"
        assert "mvp/base.html" in names
        assert "Versions of Privacy policy" in response.content.decode()

    def test_the_query_count_does_not_grow_with_the_versions_published(
        self, client, django_assert_num_queries
    ):
        few = DocumentFactory()
        for n in range(2):
            published(few, f"Wording {n}")
        many = DocumentFactory()
        for n in range(6):
            published(many, f"Wording {n}")
        client.get(reverse("mvp_compliance:versions", args=[few.slug]))  # warm caches

        with CaptureQueriesContext(connection) as small:
            client.get(reverse("mvp_compliance:versions", args=[few.slug]))
        with django_assert_num_queries(len(small)):
            client.get(reverse("mvp_compliance:versions", args=[many.slug]))
