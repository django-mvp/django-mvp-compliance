"""Tests for mvp_compliance.views."""

import re
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.formats import date_format
from mvp.menus import AppMenu

import mvp_compliance
from mvp_compliance.rendering import MarkdownRenderer
from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    UserFactory,
    VersionFactory,
)
from tests.test_admin import catalog_entries


def published(document, markdown="Wording"):
    """Publish a new version of ``document`` and return it."""
    version = VersionFactory(document=document, markdown=markdown)
    version.publish()
    return version


def document_address(document):
    return reverse("mvp_compliance:document", args=[document.slug])


def subtitle_addresses(document, first, second):
    """The document page and the page of each version of ``document``."""
    return [
        document_address(document),
        reverse("mvp_compliance:version", args=[document.slug, first.number]),
        reverse("mvp_compliance:version", args=[document.slug, second.number]),
    ]


@pytest.mark.django_db
class TestPageSubtitle:
    """FR-009: the line under a page's name is ``v<number> · published <date>``,
    continued with ``· Agreed on <date>`` for a visitor who accepted that version."""

    @staticmethod
    def line(version):
        return f"v{version.number} · published " + date_format(
            timezone.localdate(version.published_at)
        )

    def test_an_anonymous_visitor_sees_the_number_and_publication_date(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        second = published(document, "Second wording")

        for address, version in zip(
            subtitle_addresses(document, first, second),
            [second, first, second],
            strict=True,
        ):
            content = client.get(address).content.decode()
            assert self.line(version) in content
            assert "Agreed on" not in content
            assert "in force since" not in content

    def test_a_signed_in_user_with_no_acceptance_of_the_version_sees_no_agreement(
        self, client
    ):
        document = DocumentFactory()
        first = published(document, "First wording")
        second = published(document, "Second wording")
        client.force_login(UserFactory())

        for address in subtitle_addresses(document, first, second):
            assert "Agreed on" not in client.get(address).content.decode()

    def test_a_user_who_accepted_the_version_sees_the_date_they_agreed(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        second = published(document, "Second wording")
        user = UserFactory()
        agreed = timezone.now() - timedelta(days=3)
        AcceptanceFactory(user=user, version=second, accepted_at=agreed)
        client.force_login(user)
        expected = (
            f"{self.line(second)} · Agreed on {date_format(timezone.localdate(agreed))}"
        )

        for address in [
            document_address(document),
            reverse("mvp_compliance:version", args=[document.slug, second.number]),
        ]:
            assert expected in client.get(address).content.decode()
        assert first.number != second.number

    def test_a_superseded_version_carries_the_agreement_in_the_same_format(
        self, client
    ):
        document = DocumentFactory()
        first = published(document, "First wording")
        published(document, "Second wording")
        user = UserFactory()
        AcceptanceFactory(user=user, version=first)
        client.force_login(user)

        content = client.get(
            reverse("mvp_compliance:version", args=[document.slug, first.number])
        ).content.decode()

        assert f"{self.line(first)} · Agreed on " in content
        assert "replaced" in content

    def test_an_acceptance_of_another_version_of_the_document_is_not_shown(
        self, client
    ):
        document = DocumentFactory()
        first = published(document, "First wording")
        second = published(document, "Second wording")
        user = UserFactory()
        AcceptanceFactory(user=user, version=first)
        client.force_login(user)

        assert (
            "Agreed on" not in client.get(document_address(document)).content.decode()
        )
        assert (
            "Agreed on"
            not in client.get(
                reverse("mvp_compliance:version", args=[document.slug, second.number])
            ).content.decode()
        )

    def test_another_persons_acceptance_is_not_shown(self, client):
        document = DocumentFactory()
        version = published(document)
        AcceptanceFactory(user=UserFactory(), version=version)
        client.force_login(UserFactory())

        assert (
            "Agreed on" not in client.get(document_address(document)).content.decode()
        )

    @pytest.mark.parametrize("name", ["document", "version"])
    def test_the_query_count_does_not_grow_with_versions_or_acceptances(
        self, client, django_assert_num_queries, name
    ):
        user = UserFactory()
        client.force_login(user)

        def address(document, version):
            args = [document.slug] + ([version.number] if name == "version" else [])
            return reverse(f"mvp_compliance:{name}", args=args)

        one = DocumentFactory()
        only = published(one)
        AcceptanceFactory(user=user, version=only)
        many = DocumentFactory()
        latest = None
        for n in range(5):
            latest = published(many, f"Wording {n}")
            AcceptanceFactory(user=user, version=latest)
        client.get(address(one, only))  # warm caches

        with CaptureQueriesContext(connection) as single:
            client.get(address(one, only))
        with django_assert_num_queries(len(single)):
            client.get(address(many, latest))

    def test_an_anonymous_visit_costs_no_acceptance_query(self, client):
        document = DocumentFactory()
        published(document)
        client.get(document_address(document))  # warm caches

        with CaptureQueriesContext(connection) as anonymous:
            client.get(document_address(document))

        assert not [q for q in anonymous if "acceptance" in q["sql"].lower()]


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
        published(document, "Later wording")

        content = client.get(
            reverse("mvp_compliance:document", args=[document.slug])
        ).content.decode()

        address = reverse("mvp_compliance:versions", args=[document.slug])
        assert f'href="{address}"' in content
        assert "All versions" in content

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

        assert response.context["page"]["breadcrumbs"] == [
            {"text": "Legal documents", "href": reverse("mvp_compliance:index")},
            {"text": "Privacy policy"},
        ]

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
        assert f"v{current.number} · published" in document_page
        assert f"v{current.number} · published" in content

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
            {"text": "Legal documents", "href": reverse("mvp_compliance:index")},
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

        assert content.count(">In force</td>") == 1

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

    def test_the_page_renders_in_the_shell_with_the_title_of_the_document(self, client):
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


@pytest.mark.django_db
class TestDocumentIndexView:
    """A visitor finds every document that has a version in force."""

    def test_every_document_in_force_is_listed_alphabetically_and_linked(self, client):
        terms = DocumentFactory(name="Terms of use")
        cookies = DocumentFactory(name="Cookie policy")
        privacy = DocumentFactory(name="Privacy policy")
        for document in (terms, cookies, privacy):
            published(document)

        response = client.get(reverse("mvp_compliance:index"))

        assert response.status_code == 200
        assert list(response.context["documents"]) == [cookies, privacy, terms]
        content = response.content.decode()
        for document in (cookies, privacy, terms):
            address = reverse("mvp_compliance:document", args=[document.slug])
            assert f'href="{address}"' in content
        assert content.index("Cookie policy") < content.index("Privacy policy")
        assert content.index("Privacy policy") < content.index("Terms of use")

    def test_a_draft_only_document_and_an_empty_one_are_absent(self, client):
        shown = DocumentFactory(name="Privacy policy")
        published(shown)
        VersionFactory(document=DocumentFactory(name="Draft only"))
        DocumentFactory(name="Empty")

        response = client.get(reverse("mvp_compliance:index"))

        assert list(response.context["documents"]) == [shown]
        content = response.content.decode()
        assert "Draft only" not in content
        assert "Empty" not in content

    def test_with_nothing_in_force_it_says_nothing_has_been_published_yet(self, client):
        VersionFactory(document=DocumentFactory())

        response = client.get(reverse("mvp_compliance:index"))

        assert response.status_code == 200
        assert "Nothing has been published yet." in response.content.decode()

    def test_the_page_renders_in_the_shell_and_is_titled_legal_documents(self, client):
        response = client.get(reverse("mvp_compliance:index"))

        names = [template.name for template in response.templates]
        assert names[0] == "mvp_compliance/document_index.html"
        assert "mvp/base.html" in names
        assert "Legal documents" in response.content.decode()

    def test_markup_in_a_document_name_is_escaped(self, client):
        published(DocumentFactory(name="<script>alert(1)</script>"))

        content = client.get(reverse("mvp_compliance:index")).content.decode()

        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content

    def test_the_query_count_does_not_grow_with_the_documents_published(
        self, client, django_assert_num_queries
    ):
        for n in range(2):
            published(DocumentFactory(name=f"Document {n}"))
        client.get(reverse("mvp_compliance:index"))  # warm caches
        with CaptureQueriesContext(connection) as small:
            client.get(reverse("mvp_compliance:index"))
        for n in range(2, 6):
            published(DocumentFactory(name=f"Document {n}"))

        with django_assert_num_queries(len(small)):
            client.get(reverse("mvp_compliance:index"))


@pytest.mark.django_db
class TestBreadcrumbTrails:
    """Every page's trail starts at the index of documents."""

    def test_the_versions_page_leads_with_the_index_then_the_document(self, client):
        document = DocumentFactory(name="Privacy policy")
        published(document)

        response = client.get(reverse("mvp_compliance:versions", args=[document.slug]))

        assert response.context["page"]["breadcrumbs"] == [
            {"text": "Legal documents", "href": reverse("mvp_compliance:index")},
            {
                "text": "Privacy policy",
                "href": reverse("mvp_compliance:document", args=[document.slug]),
            },
            {"text": "Versions"},
        ]

    def test_the_index_is_the_root_and_its_own_trail_is_its_title(self, client):
        response = client.get(reverse("mvp_compliance:index"))

        assert response.context["page"]["breadcrumbs"] == [{"text": "Legal documents"}]


PROJECT_TEMPLATES = Path(__file__).parent / "project_templates"


@pytest.mark.django_db
class TestTemplateOverride:
    """FR-018: a project restyles a page by placing a template at the same path."""

    @pytest.fixture
    def project_templates(self, settings):
        """Point the template loaders at a directory of project templates first."""
        templates = [dict(engine) for engine in settings.TEMPLATES]
        templates[0]["DIRS"] = [PROJECT_TEMPLATES]
        settings.TEMPLATES = templates

    def test_the_document_page_renders_the_project_template(
        self, client, project_templates
    ):
        document = DocumentFactory(name="Privacy policy")
        version = published(document)

        response = client.get(reverse("mvp_compliance:document", args=[document.slug]))

        content = response.content.decode()
        assert 'id="project-document-page"' in content
        assert "Privacy policy: project override" in content
        assert version.html in content
        assert "Earlier versions" not in content

    def test_another_page_renders_the_project_template(self, client, project_templates):
        document = DocumentFactory(name="Privacy policy")
        published(document)

        response = client.get(reverse("mvp_compliance:versions", args=[document.slug]))

        assert 'id="project-version-list"' in response.content.decode()

    def test_a_page_with_no_project_template_still_renders_the_packaged_one(
        self, client, project_templates
    ):
        document = DocumentFactory()
        version = published(document)

        response = client.get(
            reverse("mvp_compliance:version", args=[document.slug, version.number])
        )

        names = [template.name for template in response.templates]
        assert names[0] == "mvp_compliance/version_detail.html"


@pytest.mark.django_db
class TestNoMenuEntry:
    """FR-014: the package adds nothing to a project's menus."""

    def test_serving_every_page_leaves_the_app_menu_unchanged(self, client):
        before = [child.name for child in AppMenu.children]
        document = DocumentFactory()
        version = published(document)

        for name, args in [
            ("index", []),
            ("document", [document.slug]),
            ("versions", [document.slug]),
            ("version", [document.slug, version.number]),
        ]:
            client.get(reverse(f"mvp_compliance:{name}", args=args))

        assert [child.name for child in AppMenu.children] == before

    def test_the_package_does_not_touch_the_menu_library(self):
        package = Path(mvp_compliance.__file__).parent

        offenders = [
            path.name
            for path in package.rglob("*.py")
            if "flex_menu" in path.read_text(encoding="utf-8")
            or "AppMenu" in path.read_text(encoding="utf-8")
        ]

        assert offenders == []


#: FR-020: no page says the site is compliant or names a regulation.
FORBIDDEN_WORDS = ("compliant", "compliance", "gdpr")

PAGE_TEMPLATES = sorted(
    (Path(mvp_compliance.__file__).parent / "templates" / "mvp_compliance").glob(
        "*.html"
    )
)
TRANSLATE_TAG = re.compile(r'{%\s*(?:translate|trans)\s+"([^"]*)"')
BLOCKTRANSLATE_TAG = re.compile(
    r"{%\s*(?:blocktranslate|blocktrans)\b[^%]*%}(.*?){%\s*(?:endblocktranslate|endblocktrans)\s*%}",
    re.DOTALL,
)
VARIABLE = re.compile(r"{{\s*(\w+)[^}]*}}")


def template_msgids(path):
    """Every msgid a page template asks for, as ``makemessages`` would write it."""
    source = path.read_text(encoding="utf-8")
    msgids = set(TRANSLATE_TAG.findall(source))
    for body in BLOCKTRANSLATE_TAG.findall(source):
        msgids.add(VARIABLE.sub(r"%(\1)s", body.strip()))
    return msgids


class TestPageStrings:
    """SC-008, FR-019, FR-020: every string the pages show is translatable, and none
    claims compliance."""

    def test_the_page_templates_are_the_four_pages(self):
        assert [path.name for path in PAGE_TEMPLATES] == [
            "document_detail.html",
            "document_index.html",
            "version_detail.html",
            "version_list.html",
        ]

    @pytest.mark.parametrize("path", PAGE_TEMPLATES, ids=lambda path: path.name)
    def test_every_string_in_a_page_template_is_in_the_english_catalog(self, path):
        msgids = template_msgids(path)
        catalog = {msgid for msgid, _msgstr in catalog_entries() if msgid}

        assert msgids
        assert msgids <= catalog

    @pytest.mark.django_db
    def test_the_version_in_force_sentence_renders_in_german(self, client):
        document = DocumentFactory()
        version = published(document)
        address = reverse(
            "mvp_compliance:version", args=[document.slug, version.number]
        )

        with translation.override("de"):
            content = client.get(address).content.decode()

        assert "Dies ist die geltende Version." in content
        assert "This is the version in force." not in content

    @pytest.mark.parametrize("path", PAGE_TEMPLATES, ids=lambda path: path.name)
    def test_no_page_string_claims_compliance_or_names_a_regulation(self, path):
        for msgid in template_msgids(path):
            lowered = msgid.lower()
            for word in FORBIDDEN_WORDS:
                assert word not in lowered, msgid

    @pytest.mark.django_db
    def test_no_rendered_page_claims_compliance_or_names_a_regulation(self, client):
        current = DocumentFactory(name="Privacy policy")
        published(current, "First wording")
        replaced = published(current, "Second wording")
        earlier = current.versions.exclude(pk=replaced.pk).get()
        addresses = [
            reverse("mvp_compliance:index"),
            reverse("mvp_compliance:document", args=[current.slug]),
            reverse("mvp_compliance:versions", args=[current.slug]),
            reverse("mvp_compliance:version", args=[current.slug, replaced.number]),
            reverse("mvp_compliance:version", args=[current.slug, earlier.number]),
        ]

        for address in addresses:
            text = re.sub(r"<[^>]+>", " ", client.get(address).content.decode())
            lowered = text.lower()
            for word in FORBIDDEN_WORDS:
                assert word not in lowered, (address, word)
