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
from mvp_compliance.models import Acceptance, Disclosure, Document, Version
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


def version_address(document, number):
    """The document's page showing the published version numbered ``number``."""
    return f"{document_address(document)}?version={number}"


def subtitle_addresses(document, first, second):
    """The document page and the page showing each version of ``document``."""
    return [
        document_address(document),
        version_address(document, first.number),
        version_address(document, second.number),
    ]


@pytest.mark.django_db
class TestPageSubtitle:
    """FR-009: the line under a page's name is ``v<number> - <date>``,
    continued with ``· Agreed on <date>`` for a visitor who accepted that version."""

    @staticmethod
    def line(version):
        return f"v{version.number} - " + date_format(
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
            version_address(document, second.number),
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

        content = client.get(version_address(document, first.number)).content.decode()

        assert f"{self.line(first)} · Agreed on " in content

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
            not in client.get(version_address(document, second.number)).content.decode()
        )

    def test_another_persons_acceptance_is_not_shown(self, client):
        document = DocumentFactory()
        version = published(document)
        AcceptanceFactory(user=UserFactory(), version=version)
        client.force_login(UserFactory())

        assert (
            "Agreed on" not in client.get(document_address(document)).content.decode()
        )

    @pytest.mark.parametrize("with_version", [False, True])
    def test_the_query_count_does_not_grow_with_versions_or_acceptances(
        self, client, django_assert_num_queries, with_version
    ):
        user = UserFactory()
        client.force_login(user)

        def address(document, version):
            return (
                version_address(document, version.number)
                if with_version
                else document_address(document)
            )

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
    """A visitor reads the version in force, or any published version by number, at
    one canonical address (FR-001, FR-002)."""

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
        assert f"v{version.number} - " in content
        assert date_format(timezone.localdate(version.published_at)) in content

    def test_the_breadcrumb_trail_is_the_documents_name_alone(self, client):
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
        assert f"v{second.number} - " in content

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

    def test_the_version_parameter_shows_that_published_versions_stored_html(
        self, client
    ):
        document = DocumentFactory()
        first = published(document, "First **bold** wording")
        second = published(document, "Second wording")

        content = client.get(version_address(document, first.number)).content.decode()

        assert first.html in content
        assert second.html not in content

    def test_the_version_in_forces_number_as_the_parameter_shows_the_same_page(
        self, client
    ):
        document = DocumentFactory()
        published(document, "First wording")
        current = published(document, "Second wording")

        without_param = client.get(document_address(document)).content.decode()
        with_param = client.get(
            version_address(document, current.number)
        ).content.decode()

        assert without_param == with_param

    def test_a_later_publication_leaves_an_earlier_versions_wording_alone(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        address = version_address(document, first.number)
        before = client.get(address).content.decode()
        assert first.html in before

        second = published(document, "Second wording")
        after = client.get(address).content.decode()

        assert first.html in after
        assert second.html not in after

    def test_a_version_parameter_belonging_to_another_document_is_not_found(
        self, client
    ):
        mine = DocumentFactory(slug="mine")
        theirs = DocumentFactory(slug="theirs")
        published(mine)
        published(theirs, "First wording")
        other = published(theirs, "Second wording")

        response = client.get(version_address(mine, other.number))

        assert response.status_code == 404

    def test_a_version_parameter_that_was_never_published_is_not_found(self, client):
        document = DocumentFactory()
        published(document)

        response = client.get(version_address(document, "1999.1"))

        assert response.status_code == 404

    def test_a_number_no_version_has_is_not_found_for_everybody(
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

        assert draft.number is None
        assert client.get(version_address(document, next_number)).status_code == 404

    def test_a_document_with_only_drafts_has_no_version_parameter_page(self, client):
        document = DocumentFactory()
        VersionFactory(document=document)

        response = client.get(version_address(document, "2026.1"))

        assert response.status_code == 404

    @pytest.mark.parametrize("number", ["", "not-a-number"])
    def test_a_malformed_version_parameter_is_not_found(self, client, number):
        document = DocumentFactory()
        published(document)

        response = client.get(version_address(document, number))

        assert response.status_code == 404

    def test_the_query_count_is_the_same_with_or_without_the_parameter(
        self, client, django_assert_num_queries
    ):
        document = DocumentFactory()
        first = published(document, "First wording")
        published(document, "Second wording")
        client.get(document_address(document))  # warm caches

        with CaptureQueriesContext(connection) as without_param:
            client.get(document_address(document))
        with django_assert_num_queries(len(without_param)):
            client.get(version_address(document, first.number))


@pytest.mark.django_db
class TestSupersededVersionAlert:
    """FR-010: a superseded version's page carries one alert row with a button back
    to the version in force; the version in force shows no such alert."""

    def test_a_superseded_version_shows_one_alert_row(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        published(document, "Second wording")

        content = client.get(version_address(document, first.number)).content.decode()

        assert content.count('role="alert"') == 1

    def test_the_alert_names_the_dates_it_was_in_force(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        second = published(document, "Second wording")
        first.refresh_from_db()

        content = client.get(version_address(document, first.number)).content.decode()

        assert date_format(timezone.localdate(first.published_at)) in content
        assert date_format(timezone.localdate(second.published_at)) in content

    def test_the_alerts_button_leads_to_the_document_page(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        published(document, "Second wording")

        content = client.get(version_address(document, first.number)).content.decode()

        assert f'href="{document_address(document)}"' in content

    def test_the_version_in_force_shows_no_alert(self, client):
        document = DocumentFactory()
        published(document)

        content = client.get(document_address(document)).content.decode()

        assert 'role="alert"' not in content

    def test_the_version_in_forces_own_number_as_the_parameter_shows_no_alert_either(
        self, client
    ):
        document = DocumentFactory()
        current = published(document)

        content = client.get(version_address(document, current.number)).content.decode()

        assert 'role="alert"' not in content


@pytest.mark.django_db
class TestVersionSwitcher:
    """FR-003, FR-011: every document page carries a version switcher among its
    actions, listing every published version newest first, the version shown
    marked active."""

    @staticmethod
    def switcher(client, address):
        content = client.get(address).content.decode()
        start = content.find("data-mvp-dropdown")
        if start == -1:
            return content, ""
        end = content.find('id="document-list"', start)
        return content, content[start:end] if end != -1 else content[start:]

    def test_every_published_version_is_listed_newest_first(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        second = published(document, "Second wording")
        third = published(document, "Third wording")

        _content, switcher = self.switcher(client, document_address(document))

        addresses = [
            f'href="{version_address(document, version.number)}"'
            for version in (third, second, first)
        ]
        positions = [switcher.index(address) for address in addresses]
        assert positions == sorted(positions)

    def test_a_draft_is_not_listed(self, client):
        document = DocumentFactory()
        published(document)
        VersionFactory(document=document, markdown="Unpublished wording")

        _content, switcher = self.switcher(client, document_address(document))

        assert switcher.count("href=") == 1

    def test_the_switcher_is_present_on_a_single_version_document(self, client):
        document = DocumentFactory()
        published(document)

        _content, switcher = self.switcher(client, document_address(document))

        assert switcher != ""

    def test_the_shown_version_is_marked_active(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        second = published(document, "Second wording")

        _content, switcher = self.switcher(
            client, version_address(document, first.number)
        )

        assert (
            f'href="{version_address(document, first.number)}" class="menu-active" aria-current="page"'
            in switcher
        )
        assert (
            f'href="{version_address(document, second.number)}" class="menu-active"'
            not in switcher
        )

    def test_the_current_version_is_marked_active_with_no_parameter(self, client):
        document = DocumentFactory()
        published(document, "First wording")
        current = published(document, "Second wording")

        _content, switcher = self.switcher(client, document_address(document))

        assert (
            f'href="{version_address(document, current.number)}" class="menu-active" aria-current="page"'
            in switcher
        )

    def test_the_triggers_text_is_the_version_shown(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        published(document, "Second wording")

        content = client.get(version_address(document, first.number)).content.decode()

        assert f"<span>v{first.number}</span>" in content


@pytest.mark.django_db
class TestDocumentList:
    """FR-004, FR-007: every document page, with or without ``?version=``, lists
    every document that has a version in force beside the wording, the one shown
    marked active."""

    @staticmethod
    def side_list(client, address):
        content = client.get(address).content.decode()
        start = content.find('<nav id="document-list"')
        end = content.find("</nav>", start)
        return content[start:end] if start != -1 else ""

    @pytest.fixture
    def documents(self):
        terms = DocumentFactory(name="Terms of use")
        cookies = DocumentFactory(name="Cookie policy")
        privacy = DocumentFactory(name="Privacy policy")
        for document in (terms, cookies, privacy):
            published(document)
        return cookies, privacy, terms

    def test_every_document_in_force_is_listed_alphabetically_and_linked(
        self, client, documents
    ):
        cookies, privacy, terms = documents

        response = client.get(document_address(privacy))

        assert list(response.context["documents"]) == [cookies, privacy, terms]
        side_list = self.side_list(client, document_address(privacy))
        addresses = [f'href="{document_address(document)}"' for document in documents]
        positions = [side_list.index(address) for address in addresses]
        assert positions == sorted(positions)

    def test_a_version_address_lists_the_same_documents(self, client, documents):
        _cookies, privacy, _terms = documents
        earlier = privacy.versions.get()
        published(privacy, "Second wording")

        side_list = self.side_list(client, version_address(privacy, earlier.number))

        for document in documents:
            assert f'href="{document_address(document)}"' in side_list

    def test_the_document_shown_is_marked_active_and_no_other(self, client, documents):
        cookies, privacy, terms = documents

        side_list = self.side_list(client, document_address(privacy))

        assert (
            f'href="{document_address(privacy)}" class="menu-active" aria-current="page"'
            in side_list
        )
        assert side_list.count("menu-active") == 1
        assert side_list.count('aria-current="page"') == 1

    def test_the_document_shown_is_marked_active_with_a_version_parameter(
        self, client, documents
    ):
        _cookies, privacy, _terms = documents
        earlier = privacy.versions.get()
        published(privacy, "Second wording")

        side_list = self.side_list(client, version_address(privacy, earlier.number))

        assert (
            f'href="{document_address(privacy)}" class="menu-active" aria-current="page"'
            in side_list
        )
        assert side_list.count("menu-active") == 1

    def test_a_draft_only_document_and_an_empty_one_are_absent(self, client):
        shown = DocumentFactory(name="Privacy policy")
        published(shown)
        VersionFactory(document=DocumentFactory(name="Draft only"))
        DocumentFactory(name="Empty")

        response = client.get(document_address(shown))

        assert list(response.context["documents"]) == [shown]
        side_list = self.side_list(client, document_address(shown))
        assert "Draft only" not in side_list
        assert "Empty" not in side_list

    @pytest.mark.parametrize("with_version", [False, True], ids=["plain", "version"])
    def test_the_query_count_does_not_grow_with_the_documents_published(
        self, client, django_assert_num_queries, with_version
    ):
        shown = DocumentFactory(name="Document 0")
        version = published(shown)
        published(DocumentFactory(name="Document 1"))
        address = (
            version_address(shown, version.number)
            if with_version
            else document_address(shown)
        )
        client.get(address)  # warm caches
        with CaptureQueriesContext(connection) as small:
            client.get(address)
        for n in range(2, 6):
            published(DocumentFactory(name=f"Document {n}"))

        with django_assert_num_queries(len(small)):
            client.get(address)


@pytest.mark.django_db
class TestNotice:
    """A notice is published to be read: its page is the same as any document's, and
    says nothing about the reader having agreed to it."""

    @pytest.fixture
    def notice(self):
        return DocumentFactory(name="Impressum", kind=Document.Kind.NOTICE)

    def test_anonymous_and_signed_in_visitors_read_the_stored_html_number_and_date(
        self, client, notice
    ):
        version = published(notice, "Some **bold** wording")
        line = f"v{version.number} - " + date_format(
            timezone.localdate(version.published_at)
        )

        for signed_in in (False, True):
            if signed_in:
                client.force_login(UserFactory())
            response = client.get(document_address(notice))

            assert response.status_code == 200
            content = response.content.decode()
            assert version.html in content
            assert line in content

    def test_a_user_who_accepted_before_it_became_a_notice_sees_no_agreement_line(
        self, client
    ):
        document = DocumentFactory()
        first = published(document, "First wording")
        user = UserFactory()
        AcceptanceFactory(user=user, version=first)
        Document.objects.filter(pk=document.pk).update(kind=Document.Kind.NOTICE)
        second = published(document, "Second wording")
        client.force_login(user)

        for address in subtitle_addresses(document, first, second):
            assert "Agreed on" not in client.get(address).content.decode()

    def test_an_earlier_version_shows_its_own_html(self, client, notice):
        first = published(notice, "First wording")
        second = published(notice, "Second wording")

        content = client.get(version_address(notice, first.number)).content.decode()

        assert first.html in content
        assert second.html not in content

    def test_the_document_list_names_a_notice_and_an_agreed_document(
        self, client, notice
    ):
        published(notice)
        agreed = DocumentFactory()
        published(agreed)

        response = client.get(document_address(notice))

        assert set(response.context["documents"]) == {notice, agreed}
        content = response.content.decode()
        assert f'href="{document_address(notice)}"' in content
        assert f'href="{document_address(agreed)}"' in content

    def test_a_notice_with_only_a_draft_is_not_found(self, client, notice):
        VersionFactory(document=notice)

        assert client.get(document_address(notice)).status_code == 404


@pytest.mark.django_db
class TestBreadcrumbTrails:
    """Every page's trail is the document's name alone."""

    def test_the_trail_is_unchanged_by_the_version_parameter(self, client):
        document = DocumentFactory(name="Privacy policy")
        first = published(document, "First wording")
        published(document, "Second wording")

        response = client.get(version_address(document, first.number))

        assert response.context["page"]["breadcrumbs"] == [{"text": "Privacy policy"}]


@pytest.mark.django_db
class TestMountRoot:
    """There is no page listing every document: the mount's root is "not found"."""

    def test_the_mount_root_is_not_found(self, client):
        published(DocumentFactory())

        assert client.get("/legal/").status_code == 404


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


@pytest.mark.django_db
class TestNoMenuEntry:
    """FR-014: the package adds nothing to a project's menus."""

    def test_serving_every_page_leaves_the_app_menu_unchanged(self, client):
        before = [child.name for child in AppMenu.children]
        document = DocumentFactory()
        version = published(document)

        for address in [
            reverse("mvp_compliance:document", args=[document.slug]),
            version_address(document, version.number),
        ]:
            client.get(address)

        assert [child.name for child in AppMenu.children] == before

    def test_the_package_does_not_touch_the_menu_library(self):
        package = Path(mvp_compliance.__file__).parent

        offenders = [
            path.name
            for path in package.rglob("*.py")
            if "AppMenu" in path.read_text(encoding="utf-8")
            or "MobileFooterMenu" in path.read_text(encoding="utf-8")
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
PLURAL_TAG = re.compile(r"{%\s*plural\s*%}")
VARIABLE = re.compile(r"{{\s*(\w+)[^}]*}}")


def template_msgids(path):
    """Every msgid a page template asks for, as ``makemessages`` would write it."""
    source = path.read_text(encoding="utf-8")
    msgids = set(TRANSLATE_TAG.findall(source))
    for body in BLOCKTRANSLATE_TAG.findall(source):
        # A plural block holds two strings, which the catalog lists apart.
        for part in PLURAL_TAG.split(body):
            msgids.add(VARIABLE.sub(r"%(\1)s", part.strip()))
    return msgids


class TestPageStrings:
    """SC-008, FR-019, FR-020: every string the pages show is translatable, and none
    claims compliance."""

    def test_the_page_template_is_the_document_page(self):
        assert [path.name for path in PAGE_TEMPLATES] == [
            "_agreed_version_rows.html",
            "agreed_documents.html",
            "document_detail.html",
        ]

    @pytest.mark.parametrize("path", PAGE_TEMPLATES, ids=lambda path: path.name)
    def test_every_string_in_a_page_template_is_in_the_english_catalog(self, path):
        msgids = template_msgids(path)
        catalog = {msgid for msgid, _msgstr in catalog_entries() if msgid}

        assert msgids <= catalog

    def test_at_least_one_page_carries_a_translatable_string(self):
        assert any(template_msgids(path) for path in PAGE_TEMPLATES)

    @pytest.mark.django_db
    def test_the_replaced_message_renders_in_german(self, client):
        document = DocumentFactory()
        first = published(document, "First wording")
        published(document, "Second wording")
        address = version_address(document, first.number)

        with translation.override("de"):
            content = client.get(address).content.decode()

        assert "wurde ersetzt" in content
        assert "has been replaced" not in content

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
            reverse("mvp_compliance:document", args=[current.slug]),
            version_address(current, replaced.number),
            version_address(current, earlier.number),
        ]

        for address in addresses:
            text = re.sub(r"<[^>]+>", " ", client.get(address).content.decode())
            lowered = text.lower()
            for word in FORBIDDEN_WORDS:
                assert word not in lowered, (address, word)


def agreed_address():
    return reverse("mvp_compliance:agreed")


def accept(user, document, count=1):
    """Publish ``count`` new versions of ``document``, accepted by ``user``, oldest first."""
    accepted = []
    for _ in range(count):
        wording = f"Wording {document.versions.count() + 1}"
        accepted.append(Acceptance.objects.record(user, published(document, wording)))
    return accepted


@pytest.mark.django_db
class TestAgreedDocuments:
    """US-1: a signed-in person's own list of what they agreed to (FR-001 to FR-008, FR-010,
    FR-011, FR-015, FR-016, FR-019, SC-001, SC-002, SC-004, SC-005)."""

    @pytest.fixture
    def signed_in(self, client, user):
        client.force_login(user)
        return client

    @staticmethod
    def listed(response):
        """What the page lists: ``[(document, [version, ...], [earlier version, ...])]``."""
        return [
            (
                entry["document"],
                [acceptance.version for acceptance in entry["shown"]],
                [acceptance.version for acceptance in entry["earlier"]],
            )
            for entry in response.context["entries"]
        ]

    def test_one_accepted_version_is_listed_with_its_number_and_the_day_it_was_accepted(
        self, signed_in, user
    ):
        document = DocumentFactory()
        (acceptance,) = accept(user, document)

        response = signed_in.get(agreed_address())

        assert response.status_code == 200
        assert self.listed(response) == [(document, [acceptance.version], [])]
        content = response.content.decode()
        assert version_address(document, acceptance.version.number) in content
        assert date_format(timezone.localdate(acceptance.accepted_at)) in content

    def test_versions_of_one_document_are_under_one_entry_newest_published_first(
        self, signed_in, user
    ):
        document = DocumentFactory()
        first, second, third = accept(user, document, 3)

        response = signed_in.get(agreed_address())

        assert self.listed(response) == [
            (document, [third.version, second.version, first.version], [])
        ]

    def test_documents_are_listed_by_name(self, signed_in, user):
        beta = DocumentFactory(name="Beta terms")
        alpha = DocumentFactory(name="Alpha terms")
        accept(user, beta)
        accept(user, alpha)

        response = signed_in.get(agreed_address())

        assert [document for document, _, _ in self.listed(response)] == [alpha, beta]

    def test_every_listed_version_links_to_its_own_page_current_and_superseded_alike(
        self, signed_in, user
    ):
        document = DocumentFactory()
        superseded, current = accept(user, document, 2)

        superseded.version.refresh_from_db()
        content = signed_in.get(agreed_address()).content.decode()

        assert superseded.version.status == superseded.version.Status.SUPERSEDED
        assert current.version.status == current.version.Status.CURRENT
        for acceptance in (superseded, current):
            address = version_address(document, acceptance.version.number)
            assert address in content

    def test_following_a_link_serves_that_versions_stored_html(self, signed_in, user):
        document = DocumentFactory()
        superseded, _current = accept(user, document, 2)

        page = signed_in.get(version_address(document, superseded.version.number))

        assert page.status_code == 200
        assert superseded.version.html in page.content.decode()

    def test_each_person_sees_only_their_own_acceptances(self, client, user):
        other = UserFactory()
        document = DocumentFactory()
        mine, theirs = accept(user, document)[0], accept(other, document)[0]

        client.force_login(user)
        mine_listed = self.listed(client.get(agreed_address()))
        client.force_login(other)
        theirs_listed = self.listed(client.get(agreed_address()))

        assert mine_listed == [(document, [mine.version], [])]
        assert theirs_listed == [(document, [theirs.version], [])]

    def test_a_staff_member_sees_only_their_own_acceptances(self, client):
        staff = UserFactory(is_staff=True, is_superuser=True)
        accept(UserFactory(), DocumentFactory())
        client.force_login(staff)

        response = client.get(agreed_address())

        assert response.status_code == 200
        assert list(response.context["entries"]) == []

    @pytest.mark.parametrize("appended", ["x/", "1/", "x/y/"])
    def test_an_address_with_anything_appended_is_not_found(self, signed_in, appended):
        response = signed_in.get(agreed_address() + appended)

        assert response.status_code == 404

    def test_nothing_in_the_query_string_names_another_person(self, client, user):
        other = UserFactory()
        accept(other, DocumentFactory())
        client.force_login(user)

        response = client.get(
            agreed_address(),
            {"user": other.pk, "subject": other.pk, "person": other.pk},
        )

        assert list(response.context["entries"]) == []

    def test_a_person_with_no_acceptances_gets_the_page_with_no_entries(
        self, signed_in
    ):
        response = signed_in.get(agreed_address())

        assert response.status_code == 200
        assert list(response.context["entries"]) == []

    def test_an_anonymous_visitor_is_sent_to_sign_in_and_sees_no_record(
        self, client, user
    ):
        document = DocumentFactory(name="Visible only to its acceptor")
        accept(user, document)

        response = client.get(agreed_address())

        assert response.status_code == 302
        assert response["Location"].startswith(reverse("account_login"))
        assert document.name not in response.content.decode()

    def test_a_document_made_a_notice_is_not_listed(self, signed_in, user):
        document = DocumentFactory()
        accept(user, document)
        Document.objects.filter(pk=document.pk).update(kind=Document.Kind.NOTICE)

        response = signed_in.get(agreed_address())

        assert list(response.context["entries"]) == []

    def test_a_document_the_person_never_accepted_is_not_listed(self, signed_in, user):
        accepted = DocumentFactory()
        accept(user, accepted)
        published(DocumentFactory())

        response = signed_in.get(agreed_address())

        assert [document for document, _, _ in self.listed(response)] == [accepted]

    def test_a_renamed_document_is_shown_under_its_present_name(self, signed_in, user):
        document = DocumentFactory(name="Old name")
        accept(user, document)
        document.name = "Present name"
        document.save()

        response = signed_in.get(agreed_address())

        assert [entry["document"].name for entry in response.context["entries"]] == [
            "Present name"
        ]
        assert "Present name" in response.content.decode()
        assert "Old name" not in response.content.decode()

    def test_markup_in_a_document_name_is_escaped(self, signed_in, user):
        document = DocumentFactory(name="<script>alert(1)</script>")
        accept(user, document)

        content = signed_in.get(agreed_address()).content.decode()

        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content

    def test_more_than_four_accepted_versions_show_the_newest_three_and_fold_the_rest(
        self, signed_in, user
    ):
        document = DocumentFactory()
        accepted = accept(user, document, 5)
        newest_first = [acceptance.version for acceptance in reversed(accepted)]

        response = signed_in.get(agreed_address())

        assert self.listed(response) == [(document, newest_first[:3], newest_first[3:])]
        content = response.content.decode()
        for version in newest_first:
            assert version_address(document, version.number) in content

    def test_four_accepted_versions_are_all_shown_and_none_folded(
        self, signed_in, user
    ):
        document = DocumentFactory()
        accepted = accept(user, document, 4)
        newest_first = [acceptance.version for acceptance in reversed(accepted)]

        response = signed_in.get(agreed_address())

        assert self.listed(response) == [(document, newest_first, [])]

    def test_the_query_count_does_not_grow_with_the_acceptances_held(
        self, client, django_assert_num_queries
    ):
        one, many = UserFactory(), UserFactory()
        accept(one, DocumentFactory())
        for _ in range(10):
            accept(many, DocumentFactory(), 5)
        client.force_login(one)
        client.get(agreed_address())  # warm caches

        with CaptureQueriesContext(connection) as single:
            client.get(agreed_address())
        client.force_login(many)
        with django_assert_num_queries(len(single)):
            client.get(agreed_address())

    def test_opening_the_page_writes_nothing(self, signed_in, user):
        accept(user, DocumentFactory(), 2)
        counts = lambda: [
            model.objects.count()
            for model in (Acceptance, Disclosure, Version, Document)
        ]
        before = counts()

        signed_in.get(agreed_address())

        assert counts() == before

    def test_posting_to_the_page_is_refused(self, signed_in, user):
        accept(user, DocumentFactory())
        before = Acceptance.objects.count()

        response = signed_in.post(agreed_address())

        assert response.status_code == 405
        assert Acceptance.objects.count() == before
