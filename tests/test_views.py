"""Tests for mvp_compliance.views."""

import io
import logging
import re
import tempfile
import time
import zipfile
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from allauth.account.internal.flows.login import AUTHENTICATION_METHODS_SESSION_KEY
from django.apps import apps
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import DatabaseError, connection
from django.templatetags.static import static
from django.test import Client, modify_settings, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import NoReverseMatch, reverse
from django.utils import timezone, translation
from django.utils.formats import date_format
from mvp.menus import AccountCenterMenu, AppMenu

import mvp_compliance
from mvp_compliance.exceptions import PersonalDataError
from mvp_compliance.models import (
    Acceptance,
    Disclosure,
    Document,
    RecordError,
    Version,
)
from mvp_compliance.personal_data import PersonalData
from mvp_compliance.rendering import MarkdownRenderer
from mvp_compliance.signals import personal_data_copied
from mvp_compliance.views import AgreementView
from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    NoteFactory,
    UserFactory,
    VersionFactory,
)
from tests.models import Note
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

    def test_a_button_among_the_actions_opens_the_panel_holding_the_list(
        self, client, documents
    ):
        _cookies, privacy, _terms = documents

        content = client.get(document_address(privacy)).content.decode()

        toggle = re.search(
            r'class="btn mvp-page-side-toggle[^"]*"\s+aria-controls="([^"]+)"', content
        )
        assert toggle is not None
        panel = content.index(f'id="{toggle.group(1)}"')
        assert panel < content.index('<nav id="document-list"')

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

TEMPLATES = Path(mvp_compliance.__file__).parent / "templates"
#: The package's page templates, and the components those pages are built from.
PAGE_TEMPLATES = sorted(
    [
        *(TEMPLATES / "mvp_compliance").glob("*.html"),
        *(TEMPLATES / "mvp_compliance" / "copy").glob("*.html"),
        *(TEMPLATES / "cotton" / "compliance").glob("*.html"),
    ],
    key=lambda path: path.name,
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
            "account_deleted.html",
            "agreed_documents.html",
            "agreement.html",
            "copy_value.html",
            "delete_account.html",
            "document_detail.html",
            "index.html",
            "outstanding.html",
            "personal_data.html",
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


@pytest.mark.django_db
class TestAgreedDocumentsStrings:
    """FR-017: the list as rendered, title, trail and menu entry included, claims nothing."""

    def test_the_rendered_list_claims_no_compliance_and_names_no_regulation(
        self, client
    ):
        user = UserFactory()
        document = DocumentFactory(name="Privacy policy")
        Acceptance.objects.record(user, published(document, "First wording"))
        published(document, "Second wording")
        client.force_login(user)

        content = client.get(agreed_address()).content.decode()

        lowered = re.sub(r"<[^>]+>", " ", content).lower()
        for word in FORBIDDEN_WORDS:
            assert word not in lowered, word


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

    def test_a_document_created_under_the_lists_slug_does_not_take_its_address(
        self, signed_in, user
    ):
        reserved = Document.objects.create(name="Agreed", slug="agreed")
        published(reserved)
        (acceptance,) = accept(user, DocumentFactory())

        response = signed_in.get(agreed_address())

        assert response.status_code == 200
        assert self.listed(response) == [
            (acceptance.version.document, [acceptance.version], [])
        ]


@pytest.mark.django_db
class TestNewerVersionInForce:
    """US-2: a listed document whose version in force the person has not accepted
    carries that version (FR-009, FR-010, FR-015, SC-003, SC-005)."""

    @pytest.fixture
    def signed_in(self, client, user):
        client.force_login(user)
        return client

    @staticmethod
    def newer(response):
        """What the page carries as ``newer``: ``{document: version in force or None}``."""
        return {
            entry["document"]: entry["newer"] for entry in response.context["entries"]
        }

    def test_a_superseded_latest_acceptance_gets_the_version_in_force_and_its_plain_address(
        self, signed_in, user
    ):
        document = DocumentFactory()
        accept(user, document)
        in_force = published(document, "Newer wording")

        response = signed_in.get(agreed_address())

        assert self.newer(response) == {document: in_force}
        content = response.content.decode()
        assert f'href="{document_address(document)}"' in content
        assert f"{document_address(document)}?version={in_force.number}" not in content

    def test_a_person_who_accepted_the_version_in_force_gets_none(
        self, signed_in, user
    ):
        document = DocumentFactory()
        accept(user, document)

        response = signed_in.get(agreed_address())

        assert self.newer(response) == {document: None}

    def test_earlier_acceptances_do_not_change_that_the_version_in_force_was_accepted(
        self, signed_in, user
    ):
        document = DocumentFactory()
        accept(user, document, 3)

        response = signed_in.get(agreed_address())

        assert self.newer(response) == {document: None}

    def test_each_document_is_judged_on_its_own_versions(self, signed_in, user):
        behind = DocumentFactory(name="Behind terms")
        level = DocumentFactory(name="Level terms")
        accept(user, behind, 2)
        accept(user, level, 2)
        in_force = published(behind)

        response = signed_in.get(agreed_address())

        assert self.newer(response) == {behind: in_force, level: None}

    def test_another_persons_acceptance_of_the_version_in_force_does_not_count(
        self, signed_in, user
    ):
        document = DocumentFactory()
        accept(user, document)
        in_force = published(document)
        Acceptance.objects.record(UserFactory(), in_force)

        response = signed_in.get(agreed_address())

        assert self.newer(response) == {document: in_force}

    def test_the_page_holds_no_form(self, signed_in, user):
        document = DocumentFactory()
        accept(user, document)
        published(document)

        response = signed_in.get(agreed_address())

        content = response.content.decode()
        listing = content[content.index('id="agreed-documents"') :]
        assert "<form" not in listing

    def test_a_version_published_between_two_requests_shows_on_the_second(
        self, signed_in, user
    ):
        document = DocumentFactory()
        accept(user, document)
        assert self.newer(signed_in.get(agreed_address())) == {document: None}

        in_force = published(document)

        assert self.newer(signed_in.get(agreed_address())) == {document: in_force}

    def test_the_query_count_does_not_grow_with_the_acceptances_held(
        self, client, django_assert_num_queries
    ):
        one, many = UserFactory(), UserFactory()
        behind = DocumentFactory()
        accept(one, behind)
        published(behind)
        for index in range(10):
            document = DocumentFactory()
            accept(many, document, 5)
            if index == 0:
                published(document)
        client.force_login(one)
        client.get(agreed_address())  # warm caches

        with CaptureQueriesContext(connection) as single:
            client.get(agreed_address())
        client.force_login(many)
        with django_assert_num_queries(len(single)):
            client.get(agreed_address())


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_package_only")
class TestWithoutTheAccountArea:
    """US-3 scenario 2, FR-013, SC-007: a project that mounts only the package's pages
    has no list, and its document pages keep working."""

    def test_the_system_checks_pass(self):
        call_command("check")

    def test_a_document_page_answers_and_holds_no_link_to_the_list(self, client):
        document = DocumentFactory()
        published(document)

        response = client.get(document_address(document))

        assert response.status_code == 200
        assert agreed_address() not in response.content.decode()

    def test_the_lists_address_is_not_found_for_a_signed_in_person(self, client, user):
        client.force_login(user)

        assert client.get(agreed_address()).status_code == 404

    def test_the_lists_address_is_not_found_for_an_anonymous_visitor(self, client):
        response = client.get(agreed_address())

        assert response.status_code == 404


def agreement_address(destination=None):
    """The page that asks, carrying ``destination`` as the address to go on to."""
    address = reverse("mvp_compliance:agree")
    if destination is None:
        return address
    return f"{address}?{urlencode({'next': destination})}"


class FormControls(HTMLParser):
    """Collects the attributes of every ``<input>`` and ``<form>`` in a page."""

    def __init__(self):
        super().__init__()
        self.inputs = []
        self.forms = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "input":
            self.inputs.append(attributes)
        elif tag == "form":
            self.forms.append(attributes)


def controls(response):
    """The page's inputs, forms and ids, parsed from the rendered response."""
    parser = FormControls()
    parser.feed(response.content.decode())
    return parser


@pytest.mark.django_db
class TestAgreement:
    """US-1: a signed-in person agrees to what is outstanding and carries on (FR-001 to
    FR-007, FR-015, FR-016, FR-019, SC-003, SC-007)."""

    @pytest.fixture
    def signed_in(self, client, user):
        client.force_login(user)
        return client

    @staticmethod
    def submission(*versions, destination="/dashboard/"):
        """A submission that lists and agrees to ``versions``."""
        ids = [version.pk for version in versions]
        return {"agree": ids, "listed": ids, "next": destination}

    def test_one_outstanding_document_is_listed_with_its_version_in_force(
        self, signed_in
    ):
        document = DocumentFactory()
        version = published(document)

        response = signed_in.get(agreement_address())

        assert response.status_code == 200
        (entry,) = response.context["entries"]
        assert entry["document"] == document
        assert entry["version"] == version

    def test_the_page_links_to_the_page_of_that_version(self, signed_in):
        document = DocumentFactory()
        first = published(document, "First wording")
        second = published(document, "Second wording")

        response = signed_in.get(agreement_address())

        content = response.content.decode()
        assert version_address(document, second.number) in content
        assert version_address(document, first.number) not in content

    def test_the_page_holds_none_of_the_versions_stored_html(self, signed_in):
        version = published(DocumentFactory(), "A clause with **emphasis** in it")

        response = signed_in.get(agreement_address())

        assert version.html
        assert version.html not in response.content.decode()

    def test_agreeing_records_one_acceptance_and_goes_on_to_the_destination(
        self, signed_in, user
    ):
        version = published(DocumentFactory())

        response = signed_in.post(
            agreement_address(),
            self.submission(version, destination="/dashboard/?tab=2"),
        )

        assert response.status_code == 302
        assert response["Location"] == "/dashboard/?tab=2"
        acceptance = Acceptance.objects.get()
        assert acceptance.version == version
        assert acceptance.subject == Acceptance.subject_of(user)

    def test_opening_the_page_records_nothing(self, signed_in):
        published(DocumentFactory())

        signed_in.get(agreement_address("/dashboard/"))

        assert not Acceptance.objects.exists()

    def test_a_submission_agreeing_to_nothing_records_nothing_and_says_so(
        self, signed_in
    ):
        version = published(DocumentFactory())

        response = signed_in.post(
            agreement_address(), {"listed": [version.pk], "next": "/dashboard/"}
        )

        assert response.status_code == 200
        assert response.context["missing"]
        assert not Acceptance.objects.exists()

    def test_a_visitor_who_is_not_signed_in_is_sent_to_sign_in_and_back(self, client):
        published(DocumentFactory())
        address = agreement_address("/dashboard/")

        response = client.get(address)

        assert response.status_code == 302
        sign_in = urlsplit(response["Location"])
        assert sign_in.path == reverse("account_login")
        assert parse_qs(sign_in.query)["next"] == [address]

    def test_an_earlier_version_accepted_leaves_the_version_in_force_outstanding(
        self, signed_in, user
    ):
        document = DocumentFactory()
        earlier = Acceptance.objects.record(user, published(document, "First"))
        second = published(document, "Second")

        listed = signed_in.get(agreement_address()).context["entries"]
        signed_in.post(agreement_address(), self.submission(second))

        assert [entry["version"] for entry in listed] == [second]
        assert Acceptance.objects.for_person(user).count() == 2
        assert Acceptance.objects.get(pk=earlier.pk).version == earlier.version

    def test_a_notice_and_a_document_with_only_a_draft_are_not_listed(self, signed_in):
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        published(notice)
        VersionFactory(document=DocumentFactory())
        # One outstanding document, so the page is drawn and not passed over.
        outstanding = DocumentFactory()
        published(outstanding)

        response = signed_in.get(agreement_address())

        listed = [entry["document"] for entry in response.context["entries"]]
        assert listed == [outstanding]

    def test_the_same_agreement_submitted_twice_leaves_one_acceptance(self, signed_in):
        version = published(DocumentFactory())
        submission = self.submission(version)

        first = signed_in.post(agreement_address(), submission)
        second = signed_in.post(agreement_address(), submission)

        assert first["Location"] == second["Location"] == "/dashboard/"
        assert Acceptance.objects.filter(version=version).count() == 1

    def test_a_submission_naming_a_version_that_was_not_listed_records_nothing(
        self, signed_in, user
    ):
        listed = published(DocumentFactory())
        document = DocumentFactory()
        superseded = published(document, "First")
        published(document, "Second")
        superseded.refresh_from_db()
        draft = VersionFactory(document=DocumentFactory())
        accepted = published(DocumentFactory())
        Acceptance.objects.record(user, accepted)
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        in_notice = published(notice)
        ids = [superseded.pk, draft.pk, accepted.pk, in_notice.pk, "not-a-number"]

        response = signed_in.post(
            agreement_address(), {"agree": ids, "listed": [listed.pk]}
        )

        assert response.status_code == 200
        assert list(Acceptance.objects.values_list("version", flat=True)) == [
            accepted.pk
        ]

    def test_a_submission_without_the_token_is_refused_and_records_nothing(self, user):
        version = published(DocumentFactory())
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        response = client.post(agreement_address(), self.submission(version))

        assert response.status_code == 403
        assert not Acceptance.objects.exists()

    def test_the_refusal_holds_in_a_project_running_no_csrf_middleware(
        self, user, settings
    ):
        settings.MIDDLEWARE = [
            name for name in settings.MIDDLEWARE if "csrf" not in name.lower()
        ]
        version = published(DocumentFactory())
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        response = client.post(agreement_address(), self.submission(version))

        assert response.status_code == 403
        assert not Acceptance.objects.exists()

    def test_the_connecting_address_is_held_when_the_project_keeps_it(self, signed_in):
        version = published(DocumentFactory())

        with override_settings(MVP_COMPLIANCE_RECORD_IP_ADDRESS=True):
            signed_in.post(
                agreement_address(),
                self.submission(version),
                REMOTE_ADDR="203.0.113.5",
            )

        assert Acceptance.objects.get().ip_address == "203.0.113.5"

    def test_no_address_is_held_by_default(self, signed_in):
        version = published(DocumentFactory())

        signed_in.post(
            agreement_address(), self.submission(version), REMOTE_ADDR="203.0.113.5"
        )

        assert Acceptance.objects.get().ip_address is None

    def test_a_document_name_containing_markup_is_escaped(self, signed_in):
        published(DocumentFactory(name="<script>alert(1)</script>"))

        content = signed_in.get(agreement_address()).content.decode()

        assert "<script>alert(1)" not in content
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content

    @pytest.mark.parametrize(
        "destination",
        [
            "https://elsewhere.example/dashboard/",
            "http://elsewhere.example/dashboard/",
            "//elsewhere.example/dashboard/",
            "javascript:alert(1)",
        ],
    )
    def test_a_destination_off_this_site_is_replaced_by_the_default(
        self, signed_in, destination
    ):
        version = published(DocumentFactory())

        shown = signed_in.get(agreement_address(destination))
        sent = signed_in.post(
            agreement_address(), self.submission(version, destination=destination)
        )

        assert shown.context["destination"] == "/"
        assert sent["Location"] == "/"

    def test_the_page_carries_the_hooks_the_script_depends_on(self, signed_in):
        published(DocumentFactory())
        published(DocumentFactory())

        response = signed_in.get(agreement_address())

        page = controls(response)
        assert "agreement" in [form.get("id") for form in page.forms]
        toggles = [field for field in page.inputs if field.get("name") == "agree"]
        assert len(toggles) == 2
        for toggle in toggles:
            assert "data-required" in toggle
            assert toggle["aria-describedby"] in page.ids
        assert static("mvp_compliance/agreement.js") in response.content.decode()

    def test_a_document_created_under_the_slug_agree_does_not_take_the_address(
        self, signed_in
    ):
        document = DocumentFactory(slug="agree")
        published(document)

        response = signed_in.get(agreement_address())

        assert response.status_code == 200
        assert response.templates[0].name == "mvp_compliance/agreement.html"
        (entry,) = response.context["entries"]
        assert entry["document"] == document


@pytest.mark.django_db
class TestAgreementNotRecorded:
    """US-2: a submission whose acceptances could not be stored is asked again (FR-008
    to FR-011, SC-002, SC-005)."""

    @pytest.fixture
    def signed_in(self, client, user):
        client.force_login(user)
        return client

    @staticmethod
    def submission(*versions, destination="/dashboard/"):
        """A submission that lists and agrees to ``versions``."""
        ids = [version.pk for version in versions]
        return {"agree": ids, "listed": ids, "next": destination}

    @staticmethod
    def failing(error):
        """Make the write of the page's acceptances raise ``error``."""
        return patch.object(AgreementView, "record_agreed", side_effect=error)

    @pytest.mark.parametrize("error", [DatabaseError, RecordError])
    def test_a_failed_write_shows_the_page_again_and_records_nothing(
        self, signed_in, user, error
    ):
        document = DocumentFactory()
        version = published(document)

        with self.failing(error("the write failed")):
            response = signed_in.post(agreement_address(), self.submission(version))

        assert response.status_code == 200
        assert response.context["failed"]
        assert not Acceptance.objects.exists()
        assert list(Document.objects.outstanding_for(user)) == [document]

    def test_the_toggles_that_were_on_come_back_on(self, signed_in):
        agreed = published(DocumentFactory())
        left_off = published(DocumentFactory())

        with self.failing(DatabaseError("the write failed")):
            response = signed_in.post(
                agreement_address(),
                {
                    "agree": [agreed.pk],
                    "listed": [agreed.pk, left_off.pk],
                    "next": "/dashboard/",
                },
            )

        toggles = {
            field["value"]: field
            for field in controls(response).inputs
            if field.get("name") == "agree"
        }
        assert "checked" in toggles[str(agreed.pk)]
        assert "checked" not in toggles[str(left_off.pk)]

    def test_submitting_again_once_the_write_works_goes_on_to_the_destination(
        self, signed_in
    ):
        version = published(DocumentFactory())
        submission = self.submission(version, destination="/dashboard/?tab=2")

        with self.failing(DatabaseError("the write failed")):
            signed_in.post(agreement_address(), submission)
        response = signed_in.post(agreement_address(), submission)

        assert response.status_code == 302
        assert response["Location"] == "/dashboard/?tab=2"
        assert Acceptance.objects.get().version == version

    @pytest.mark.parametrize("error", [DatabaseError, RecordError])
    def test_the_failure_is_logged_with_its_cause_and_kept_from_the_page(
        self, signed_in, caplog, error
    ):
        version = published(DocumentFactory())
        cause = error("secret cause of the failure")

        with (
            caplog.at_level(logging.ERROR, logger="mvp_compliance.views"),
            self.failing(cause),
        ):
            response = signed_in.post(agreement_address(), self.submission(version))

        (record,) = [
            record for record in caplog.records if record.name == "mvp_compliance.views"
        ]
        assert record.levelno == logging.ERROR
        assert record.exc_info[1] is cause
        assert "secret cause of the failure" not in response.content.decode()

    def test_a_write_that_stores_nothing_and_raises_nothing_does_not_let_through(
        self, signed_in
    ):
        version = published(DocumentFactory())

        with patch.object(AgreementView, "record_agreed", return_value=None):
            response = signed_in.post(agreement_address(), self.submission(version))

        assert response.status_code == 200
        assert not Acceptance.objects.exists()

    def test_a_failure_after_some_acceptances_were_written_keeps_none_of_them(
        self, signed_in
    ):
        versions = [published(DocumentFactory()) for _ in range(3)]

        def write_all_then_fail(view, versions):
            Acceptance.objects.record_many(view.request.user, versions)
            raise DatabaseError("the third write failed")

        with patch.object(AgreementView, "record_agreed", write_all_then_fail):
            response = signed_in.post(agreement_address(), self.submission(*versions))

        assert response.status_code == 200
        assert not Acceptance.objects.exists()


@pytest.mark.django_db
class TestSeveralOutstanding:
    """US-3: several outstanding documents agreed to in one sitting (FR-003 to FR-005,
    FR-010, FR-012 to FR-014, FR-023, SC-004, SC-009)."""

    @pytest.fixture
    def signed_in(self, client, user):
        client.force_login(user)
        return client

    @staticmethod
    def submission(listed, agreed=None, destination="/dashboard/"):
        """A submission listing ``listed`` and agreeing to ``agreed`` (default: all)."""
        agreed = listed if agreed is None else agreed
        return {
            "agree": [version.pk for version in agreed],
            "listed": [version.pk for version in listed],
            "next": destination,
        }

    @staticmethod
    def toggles(response):
        """The page's agree toggles, by the version id they carry."""
        return {
            field["value"]: field
            for field in controls(response).inputs
            if field.get("name") == "agree"
        }

    @pytest.fixture
    def optional(self, monkeypatch):
        """Make ``is_optional`` answer true for the documents put in the set."""
        chosen = set()
        monkeypatch.setattr(
            AgreementView, "is_optional", lambda view, document: document.pk in chosen
        )
        return chosen

    def test_each_entry_links_to_its_own_current_version(self, signed_in):
        documents = [DocumentFactory() for _ in range(3)]
        replaced = []
        current = []
        for document in documents:
            replaced.append(published(document, "First"))
            current.append(published(document, "Second"))

        response = signed_in.get(agreement_address())

        entries = response.context["entries"]
        assert [entry["document"] for entry in entries] == sorted(
            documents, key=lambda document: document.name
        )
        assert {entry["version"] for entry in entries} == set(current)
        content = response.content.decode()
        for document, before, version in zip(documents, replaced, current, strict=True):
            assert version_address(document, version.number) in content
            assert version_address(document, before.number) not in content

    def test_agreeing_to_all_of_them_records_each_and_redirects_once(
        self, signed_in, user
    ):
        versions = [published(DocumentFactory()) for _ in range(3)]

        response = signed_in.post(agreement_address(), self.submission(versions))

        assert response.status_code == 302
        assert response["Location"] == "/dashboard/"
        recorded = Acceptance.objects.for_person(user)
        assert set(recorded.values_list("version", flat=True)) == {
            version.pk for version in versions
        }
        assert recorded.count() == 3

    def test_agreeing_to_two_records_them_and_lists_only_the_third(
        self, signed_in, user
    ):
        first, second, third = (
            published(DocumentFactory(name=name)) for name in ("A", "B", "C")
        )

        response = signed_in.post(
            agreement_address(),
            self.submission([first, second, third], [first, second]),
        )

        assert response.status_code == 200
        assert response.context["missing"]
        assert [entry["version"] for entry in response.context["entries"]] == [third]
        assert set(Acceptance.objects.values_list("version", flat=True)) == {
            first.pk,
            second.pk,
        }

    def test_agreeing_to_the_third_goes_to_the_destination_first_given(self, signed_in):
        first, second = (published(DocumentFactory(name=n)) for n in ("A", "B"))
        opened = signed_in.get(agreement_address("/dashboard/?tab=2"))
        destination = opened.context["destination"]

        again = signed_in.post(
            agreement_address(),
            self.submission([first, second], [first], destination=destination),
        )
        response = signed_in.post(
            agreement_address(),
            self.submission([second], destination=again.context["destination"]),
        )

        assert again.status_code == 200
        assert response.status_code == 302
        assert response["Location"] == "/dashboard/?tab=2"

    def test_entries_are_in_name_order_on_every_request(self, signed_in):
        versions = {
            name: published(DocumentFactory(name=name))
            for name in ("Charlie", "Alpha", "Delta", "Bravo")
        }
        names = ["Alpha", "Bravo", "Charlie", "Delta"]

        opened = signed_in.get(agreement_address())
        asked_again = signed_in.post(
            agreement_address(),
            self.submission(list(versions.values()), [versions["Bravo"]]),
        )

        assert [entry["document"].name for entry in opened.context["entries"]] == names
        assert [entry["document"].name for entry in asked_again.context["entries"]] == [
            "Alpha",
            "Charlie",
            "Delta",
        ]

    def test_a_version_published_after_the_page_was_drawn_is_not_recorded(
        self, signed_in, user
    ):
        replaced = DocumentFactory(name="A")
        old = published(replaced, "Old")
        kept = published(DocumentFactory(name="B"))
        listed = self.submission([old, kept])
        new = published(replaced, "New")

        response = signed_in.post(agreement_address(), listed)

        assert response.status_code == 200
        assert response.context["changed"]
        assert not response.context.get("missing")
        assert [entry["version"] for entry in response.context["entries"]] == [new]
        assert list(Acceptance.objects.values_list("version", flat=True)) == [kept.pk]

    def test_a_document_published_after_the_page_was_drawn_is_listed_as_changed(
        self, signed_in
    ):
        drawn = published(DocumentFactory(name="A"))
        listed = self.submission([drawn])
        added = published(DocumentFactory(name="B"))

        response = signed_in.post(agreement_address(), listed)

        assert response.status_code == 200
        assert response.context["changed"]
        assert not response.context.get("missing")
        assert [entry["version"] for entry in response.context["entries"]] == [added]
        assert list(Acceptance.objects.values_list("version", flat=True)) == [drawn.pk]

    def test_a_submission_that_lists_nothing_is_drawn_as_changed(self, signed_in):
        first, second = (published(DocumentFactory(name=name)) for name in ("A", "B"))
        submission = {"agree": [first.pk], "next": "/dashboard/"}

        response = signed_in.post(agreement_address(), submission)

        assert response.status_code == 200
        assert response.context["changed"]
        assert not response.context.get("missing")
        assert [entry["version"] for entry in response.context["entries"]] == [second]

    def test_a_document_no_longer_outstanding_is_passed_over(self, signed_in, user):
        elsewhere, became_notice, kept, left = (
            published(DocumentFactory(name=name)) for name in ("A", "B", "C", "D")
        )
        listed = [elsewhere, became_notice, kept, left]
        submission = self.submission(listed, [elsewhere, became_notice, kept])
        Acceptance.objects.record(user, elsewhere)
        Document.objects.filter(pk=became_notice.document_id).update(
            kind=Document.Kind.NOTICE
        )

        response = signed_in.post(agreement_address(), submission)

        assert response.status_code == 200
        assert not response.context.get("failed")
        assert not response.context.get("changed")
        assert set(Acceptance.objects.values_list("version", flat=True)) == {
            elsewhere.pk,
            kept.pk,
        }
        assert [entry["version"] for entry in response.context["entries"]] == [left]

    def test_the_query_count_of_opening_the_page_does_not_grow_with_the_documents(
        self, signed_in
    ):
        published(DocumentFactory())
        signed_in.get(agreement_address())  # warm caches
        with CaptureQueriesContext(connection) as small:
            signed_in.get(agreement_address())
        for _ in range(9):
            published(DocumentFactory())

        with CaptureQueriesContext(connection) as large:
            signed_in.get(agreement_address())

        assert len(large) == len(small)

    def test_the_query_count_of_agreeing_to_all_does_not_grow_with_the_documents(
        self, signed_in
    ):
        warm = [published(DocumentFactory()) for _ in range(2)]
        signed_in.post(agreement_address(), self.submission(warm))
        one = [published(DocumentFactory())]
        with CaptureQueriesContext(connection) as small:
            signed_in.post(agreement_address(), self.submission(one))
        ten = [published(DocumentFactory()) for _ in range(10)]

        with CaptureQueriesContext(connection) as large:
            signed_in.post(agreement_address(), self.submission(ten))

        assert len(large) == len(small)

    def test_an_optional_entry_is_marked_so_and_its_toggle_is_not_required(
        self, signed_in, optional
    ):
        required = published(DocumentFactory(name="A"))
        agreed_either_way = published(DocumentFactory(name="B"))
        optional.add(agreed_either_way.document_id)

        response = signed_in.get(agreement_address())

        marked = {
            entry["version"]: entry["optional"] for entry in response.context["entries"]
        }
        assert marked == {required: False, agreed_either_way: True}
        toggles = self.toggles(response)
        assert "data-required" in toggles[str(required.pk)]
        assert "data-required" not in toggles[str(agreed_either_way.pk)]

    def test_agreeing_to_only_the_required_one_goes_on(self, signed_in, optional):
        required = published(DocumentFactory(name="A"))
        left = published(DocumentFactory(name="B"))
        optional.add(left.document_id)

        response = signed_in.post(
            agreement_address(), self.submission([required, left], [required])
        )

        assert response.status_code == 302
        assert list(Acceptance.objects.values_list("version", flat=True)) == [
            required.pk
        ]

    def test_agreeing_to_only_the_optional_one_records_it_and_asks_again(
        self, signed_in, optional
    ):
        required = published(DocumentFactory(name="A"))
        agreed = published(DocumentFactory(name="B"))
        optional.add(agreed.document_id)

        response = signed_in.post(
            agreement_address(), self.submission([required, agreed], [agreed])
        )

        assert response.status_code == 200
        assert response.context["missing"]
        assert list(Acceptance.objects.values_list("version", flat=True)) == [agreed.pk]

    def test_a_page_of_only_optional_documents_goes_on_with_nothing_agreed(
        self, signed_in, optional
    ):
        versions = [published(DocumentFactory()) for _ in range(2)]
        optional.update(version.document_id for version in versions)

        opened = signed_in.get(agreement_address())
        response = signed_in.post(agreement_address(), self.submission(versions, []))

        assert opened.status_code == 200
        assert response.status_code == 302
        assert not Acceptance.objects.exists()


@pytest.mark.django_db
class TestAgreementDestination:
    """US-4: where a person is sent on to, and the person with nothing outstanding
    (FR-015 to FR-018, FR-026, SC-006)."""

    default = "/welcome/"

    @pytest.fixture
    def signed_in(self, client, user):
        client.force_login(user)
        return client

    @pytest.fixture
    def project_default(self, settings):
        """The project's own default destination, set to a path."""
        settings.MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL = self.default

    @staticmethod
    def submission(listed, agreed=None, destination="/dashboard/"):
        """A submission listing ``listed`` and agreeing to ``agreed`` (default: all)."""
        agreed = listed if agreed is None else agreed
        return {
            "agree": [version.pk for version in agreed],
            "listed": [version.pk for version in listed],
            "next": destination,
        }

    @staticmethod
    def carried(response):
        """The destination the page's form carries for the next submission."""
        (field,) = [
            field for field in controls(response).inputs if field.get("name") == "next"
        ]
        return field["value"]

    def test_agreeing_to_everything_goes_on_to_a_destination_on_the_site(
        self, signed_in
    ):
        version = published(DocumentFactory())

        response = signed_in.post(
            agreement_address(),
            self.submission([version], destination="/checkout/?step=2"),
        )

        assert response.status_code == 302
        assert response["Location"] == "/checkout/?step=2"

    def test_a_person_with_nothing_outstanding_is_sent_on_and_shown_nothing(
        self, signed_in, user
    ):
        Acceptance.objects.record(user, published(DocumentFactory()))

        response = signed_in.get(agreement_address("/checkout/?step=2"))

        assert response.status_code == 302
        assert response["Location"] == "/checkout/?step=2"
        assert response.content == b""
        assert not response.templates

    def test_a_person_with_nothing_outstanding_and_no_destination_gets_the_default(
        self, signed_in, project_default
    ):
        response = signed_in.get(agreement_address())

        assert response.status_code == 302
        assert response["Location"] == self.default

    def test_nothing_outstanding_and_a_foreign_destination_gives_the_default(
        self, signed_in, project_default
    ):
        response = signed_in.get(agreement_address("https://elsewhere.example/"))

        assert response.status_code == 302
        assert response["Location"] == self.default

    @pytest.mark.parametrize(
        "destination",
        [
            "https://elsewhere.example/checkout/",
            "//elsewhere.example/checkout/",
            "javascript:alert(1)",
        ],
    )
    def test_a_destination_on_another_site_is_replaced_by_the_default(
        self, signed_in, project_default, destination
    ):
        version = published(DocumentFactory())

        shown = signed_in.get(agreement_address(destination))
        sent = signed_in.post(
            agreement_address(), self.submission([version], destination=destination)
        )

        assert shown.context["destination"] == self.default
        assert self.carried(shown) == self.default
        assert sent["Location"] == self.default

    def test_no_destination_gives_the_default(self, signed_in, project_default):
        version = published(DocumentFactory())

        shown = signed_in.get(agreement_address())
        sent = signed_in.post(
            agreement_address(), self.submission([version], destination="")
        )

        assert shown.context["destination"] == self.default
        assert sent["Location"] == self.default

    def test_with_no_setting_the_default_is_the_site_root(self, signed_in):
        version = published(DocumentFactory())

        sent = signed_in.post(
            agreement_address(), self.submission([version], destination="")
        )

        assert sent["Location"] == "/"

    @pytest.mark.parametrize(
        "default, address",
        [
            ("/welcome/", "/welcome/"),
            ("mvp_compliance:agreed", "/legal/agreed/"),
        ],
    )
    def test_the_default_is_the_path_or_url_name_the_project_set(
        self, signed_in, settings, default, address
    ):
        settings.MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL = default
        version = published(DocumentFactory())

        sent = signed_in.post(
            agreement_address(), self.submission([version], destination="")
        )

        assert sent["Location"] == address

    @pytest.mark.parametrize(
        "destination",
        [
            "/legal/agree/",
            "/legal/agree/?x=1",
            "/legal/agree",
            "/legal/%61gree/",
            ".",
            "?x=1",
            "/legal/agree/%2e",
            "/legal/x/%2e%2e/agree/",
        ],
        ids=[
            "the address",
            "with a query string",
            "without the trailing slash",
            "with a percent-encoded letter",
            "as a dot",
            "as a bare query string",
            "with a percent-encoded dot",
            "through percent-encoded parent segments",
        ],
    )
    def test_the_pages_own_address_is_replaced_by_the_default(
        self, signed_in, project_default, destination
    ):
        version = published(DocumentFactory())

        shown = signed_in.get(agreement_address(destination))
        sent = signed_in.post(
            agreement_address(), self.submission([version], destination=destination)
        )

        assert shown.context["destination"] == self.default
        assert sent["Location"] == self.default

    def test_an_address_that_only_starts_like_the_page_is_followed(self, signed_in):
        version = published(DocumentFactory())

        sent = signed_in.post(
            agreement_address(),
            self.submission([version], destination="/legal/agree/more/"),
        )

        assert sent["Location"] == "/legal/agree/more/"

    def test_the_destination_first_given_is_in_the_form_after_a_failed_write(
        self, signed_in
    ):
        version = published(DocumentFactory())
        opened = signed_in.get(agreement_address("/checkout/?step=2"))

        with patch.object(AgreementView, "record_agreed", side_effect=DatabaseError):
            failed = signed_in.post(
                agreement_address(),
                self.submission([version], destination=self.carried(opened)),
            )
        sent = signed_in.post(
            agreement_address(),
            self.submission([version], destination=self.carried(failed)),
        )

        assert failed.status_code == 200
        assert self.carried(opened) == self.carried(failed) == "/checkout/?step=2"
        assert sent["Location"] == "/checkout/?step=2"

    def test_the_destination_first_given_is_in_the_form_after_a_partial_agreement(
        self, signed_in
    ):
        first, second = (published(DocumentFactory(name=n)) for n in ("A", "B"))
        opened = signed_in.get(agreement_address("/checkout/?step=2"))

        partial = signed_in.post(
            agreement_address(),
            self.submission([first, second], [first], destination=self.carried(opened)),
        )
        sent = signed_in.post(
            agreement_address(),
            self.submission([second], destination=self.carried(partial)),
        )

        assert partial.status_code == 200
        assert self.carried(partial) == "/checkout/?step=2"
        assert sent["Location"] == "/checkout/?step=2"

    def test_a_default_given_by_the_first_visit_is_what_a_later_submission_follows(
        self, signed_in, project_default
    ):
        version = published(DocumentFactory())
        opened = signed_in.get(agreement_address())

        sent = signed_in.post(
            agreement_address(),
            self.submission([version], destination=self.carried(opened)),
        )

        assert self.carried(opened) == self.default
        assert sent["Location"] == self.default


@pytest.mark.django_db
class TestAgreementInAProject:
    """US-5 scenarios 1 to 3, FR-020, FR-021: the page belongs to the project's shell,
    its template can be replaced, and a project that mounts no package page is
    unaffected."""

    @pytest.fixture
    def signed_in(self, client, user):
        client.force_login(user)
        return client

    @pytest.fixture
    def project_templates(self, settings):
        """Point the template loaders at a directory of project templates first."""
        templates = [dict(engine) for engine in settings.TEMPLATES]
        templates[0]["DIRS"] = [PROJECT_TEMPLATES]
        settings.TEMPLATES = templates

    @staticmethod
    def submission(response):
        """What a browser sends from the page: every field, every toggle on."""
        data: dict[str, list[str]] = {}
        for field in controls(response).inputs:
            if "name" in field:
                data.setdefault(field["name"], []).append(field.get("value", ""))
        return data

    def test_the_page_renders_in_the_shell_with_no_project_template(self, signed_in):
        published(DocumentFactory())

        response = signed_in.get(agreement_address())

        names = [template.name for template in response.templates]
        assert names[0] == "mvp_compliance/agreement.html"
        assert "page_view.html" in names
        assert "mvp/base.html" in names

    def test_the_page_renders_the_project_template(self, signed_in, project_templates):
        document = DocumentFactory()
        published(document)

        response = signed_in.get(agreement_address())

        assert "project-agreement-page" in controls(response).ids
        (entry,) = response.context["entries"]
        assert entry["document"] == document

    def test_a_submission_from_the_project_template_records_and_goes_on(
        self, signed_in, project_templates, user
    ):
        version = published(DocumentFactory())
        opened = signed_in.get(agreement_address("/dashboard/"))

        response = signed_in.post(agreement_address(), self.submission(opened))

        assert response.status_code == 302
        assert response["Location"] == "/dashboard/"
        acceptance = Acceptance.objects.get()
        assert acceptance.version == version
        assert acceptance.subject == Acceptance.subject_of(user)

    @pytest.mark.urls("tests.urls_mvp_only")
    def test_a_project_mounting_only_django_mvp_passes_the_system_checks(self):
        call_command("check")

    @pytest.mark.urls("tests.urls_mvp_only")
    def test_a_project_mounting_only_django_mvp_still_records_from_code(self, user):
        version = published(DocumentFactory())

        Acceptance.objects.record(user, version)

        assert Acceptance.objects.get().version == version


@pytest.mark.django_db
class TestAgreementStrings:
    """FR-025: the page as rendered, title and trail included, claims nothing."""

    def test_the_rendered_page_claims_no_compliance_and_names_no_regulation(
        self, client, user
    ):
        published(DocumentFactory(name="Privacy policy"))
        client.force_login(user)

        content = client.get(agreement_address()).content.decode()

        lowered = re.sub(r"<[^>]+>", " ", content).lower()
        for word in FORBIDDEN_WORDS:
            assert word not in lowered, word


@pytest.mark.django_db
class TestAgreementEnforcement:
    """US-3: the page that asks follows each document's enforcement, so it lets a
    person go exactly when the check does (FR-015, FR-028 to FR-032, SC-008,
    SC-009)."""

    default = "/welcome/"

    @pytest.fixture(autouse=True)
    def project_default(self, settings):
        settings.MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL = self.default

    @pytest.fixture
    def signed_in(self, client, user):
        client.force_login(user)
        return client

    @pytest.fixture
    def enforced(self):
        """The version in force of a document that stops a person."""
        return published(DocumentFactory())

    @pytest.fixture
    def unenforced(self):
        """The version in force of a document that is offered and never required."""
        return published(DocumentFactory(enforced=False))

    @staticmethod
    def submission(listed, agreed=None, destination="/dashboard/"):
        """A submission listing ``listed`` and agreeing to ``agreed`` (default: all)."""
        agreed = listed if agreed is None else agreed
        return {
            "agree": [version.pk for version in agreed],
            "listed": [version.pk for version in listed],
            "next": destination,
        }

    def test_agreeing_to_the_enforced_document_only_records_it_and_goes_on(
        self, signed_in, user, enforced, unenforced
    ):
        response = signed_in.post(
            agreement_address(),
            self.submission([enforced, unenforced], agreed=[enforced]),
        )

        assert response.status_code == 302
        assert response["Location"] == "/dashboard/"
        (acceptance,) = Acceptance.objects.for_person(user)
        assert acceptance.version == enforced

    def test_agreeing_to_both_records_both_and_goes_on(
        self, signed_in, user, enforced, unenforced
    ):
        response = signed_in.post(
            agreement_address(), self.submission([enforced, unenforced])
        )

        assert response.status_code == 302
        assert response["Location"] == "/dashboard/"
        recorded = {acceptance.version for acceptance in Acceptance.objects.all()}
        assert recorded == {enforced, unenforced}

    def test_agreeing_to_one_of_two_enforced_documents_shows_the_other(
        self, signed_in, user, enforced
    ):
        other = published(DocumentFactory())

        response = signed_in.post(
            agreement_address(), self.submission([enforced, other], agreed=[enforced])
        )

        assert response.status_code == 200
        (entry,) = response.context["entries"]
        assert entry["version"] == other
        assert not entry["optional"]
        assert Acceptance.objects.get().version == enforced

    def test_agreeing_to_the_unenforced_document_only_records_it_and_asks_again(
        self, signed_in, user, enforced, unenforced
    ):
        response = signed_in.post(
            agreement_address(),
            self.submission([enforced, unenforced], agreed=[unenforced]),
        )

        assert response.status_code == 200
        (entry,) = response.context["entries"]
        assert entry["version"] == enforced
        assert Acceptance.objects.get().version == unenforced

    def test_the_page_lists_both_and_only_the_unenforced_one_is_optional(
        self, signed_in, enforced, unenforced
    ):
        response = signed_in.get(agreement_address())

        assert response.status_code == 200
        optional = {
            entry["document"]: entry["optional"]
            for entry in response.context["entries"]
        }
        assert optional == {
            enforced.document: False,
            unenforced.document: True,
        }

    def test_the_required_entries_are_the_enforced_outstanding_documents(
        self, signed_in, user, enforced, unenforced
    ):
        published(DocumentFactory())
        Acceptance.objects.record(user, published(DocumentFactory()))
        published(DocumentFactory(kind=Document.Kind.NOTICE))

        response = signed_in.get(agreement_address())

        required = {
            entry["document"]
            for entry in response.context["entries"]
            if not entry["optional"]
        }
        assert required == set(Document.objects.enforced_outstanding_for(user))
        assert len(required) == 2

    @pytest.mark.parametrize(
        "destination", ["/checkout/?step=2", "https://elsewhere.example/", ""]
    )
    def test_only_unenforced_outstanding_and_an_address_sends_on_at_once(
        self, signed_in, unenforced, destination
    ):
        response = signed_in.get(agreement_address(destination))

        assert response.status_code == 302
        assert response.content == b""
        assert not response.templates
        expected = destination if destination.startswith("/") else self.default
        assert response["Location"] == expected

    def test_only_unenforced_outstanding_and_no_address_shows_the_page(
        self, signed_in, unenforced
    ):
        response = signed_in.get(agreement_address())

        assert response.status_code == 200
        (entry,) = response.context["entries"]
        assert entry["version"] == unenforced
        assert entry["optional"]

    def test_agreeing_to_the_only_unenforced_document_records_it_and_goes_on(
        self, signed_in, user, unenforced
    ):
        response = signed_in.post(
            agreement_address(), self.submission([unenforced], destination="")
        )

        assert response.status_code == 302
        assert response["Location"] == self.default
        assert Acceptance.objects.get().version == unenforced

    def test_agreeing_to_nothing_goes_on_to_the_default_destination(
        self, signed_in, unenforced
    ):
        response = signed_in.post(
            agreement_address(),
            self.submission([unenforced], agreed=[], destination=""),
        )

        assert response.status_code == 302
        assert response["Location"] == self.default
        assert not Acceptance.objects.exists()

    @pytest.mark.parametrize("destination", [None, "/checkout/", ""])
    def test_nothing_outstanding_sends_on_with_or_without_an_address(
        self, signed_in, user, destination
    ):
        Acceptance.objects.record(user, published(DocumentFactory()))
        Acceptance.objects.record(user, published(DocumentFactory(enforced=False)))

        response = signed_in.get(agreement_address(destination))

        assert response.status_code == 302
        assert response.content == b""

    def test_a_failed_write_sends_nobody_on_and_records_neither_document(
        self, signed_in, enforced, unenforced
    ):
        with patch.object(
            AgreementView, "record_agreed", side_effect=DatabaseError("failed")
        ):
            response = signed_in.post(
                agreement_address(), self.submission([enforced, unenforced])
            )

        assert response.status_code == 200
        assert response.context["failed"]
        assert not Acceptance.objects.exists()

    def test_enforcement_switched_off_after_the_page_was_drawn_is_honoured(
        self, signed_in, enforced
    ):
        other = published(DocumentFactory())
        Document.objects.filter(pk=other.document_id).update(enforced=False)

        response = signed_in.post(
            agreement_address(), self.submission([enforced, other], agreed=[enforced])
        )

        assert response.status_code == 302
        assert response["Location"] == "/dashboard/"

    def test_enforcement_switched_on_after_the_page_was_drawn_is_honoured(
        self, signed_in, enforced, unenforced
    ):
        Document.objects.filter(pk=unenforced.document_id).update(enforced=True)

        response = signed_in.post(
            agreement_address(),
            self.submission([enforced, unenforced], agreed=[enforced]),
        )

        assert response.status_code == 200
        (entry,) = response.context["entries"]
        assert entry["version"] == unenforced
        assert not entry["optional"]

    def test_a_stopped_person_agrees_to_the_enforced_document_and_arrives(
        self, signed_in, user, enforced, unenforced
    ):
        asked_for = reverse("account-center")

        with modify_settings(
            MIDDLEWARE={"append": "mvp_compliance.middleware.AgreementMiddleware"}
        ):
            stopped = signed_in.get(asked_for)
            opened = signed_in.get(stopped["Location"])
            sent = signed_in.post(
                agreement_address(),
                self.submission(
                    [enforced, unenforced],
                    agreed=[enforced],
                    destination=opened.context["destination"],
                ),
            )
            arrived = signed_in.get(sent["Location"])

        assert stopped.status_code == 302
        assert opened.status_code == 200
        assert sent["Location"] == asked_for
        assert arrived.status_code == 200
        (acceptance,) = Acceptance.objects.for_person(user)
        assert acceptance.version == enforced


def personal_data_address():
    return reverse("mvp_compliance:personal-data")


def confirm(client):
    """Record, as allauth's confirmation page does, that the person just confirmed."""
    session = client.session
    session[AUTHENTICATION_METHODS_SESSION_KEY] = [
        {"method": "password", "at": time.time(), "reauthenticated": True}
    ]
    session.save()


def listed_kinds(response):
    """The keys of the kinds the page lists, in the order it lists them."""
    return re.findall(r'data-section="([^"]+)"', response.content.decode())


@pytest.fixture
def collects():
    """Every ``collect`` the declared test kinds have, replaced by a recording mock."""
    with (
        patch.object(PersonalData, "collect") as base,
        patch("tests.kinds.Custom.collect") as custom,
    ):
        yield [base, custom]


@pytest.mark.django_db
class TestPersonalDataPage:
    """US-1 scenarios 1 to 4, FR-001 to FR-003, FR-009, FR-010, FR-011, FR-016."""

    def test_without_a_declaration_the_route_does_not_exist_and_no_menu_entry_leads_to_it(
        self, rf, user
    ):
        request = rf.get(reverse("account-center"))
        request.user = user

        with pytest.raises(NoReverseMatch):
            personal_data_address()
        assert "personal-data" not in [
            child.name for child in AccountCenterMenu.process(request).children
        ]

    def test_with_a_declaration_the_route_resolves_and_the_menu_leads_to_it(
        self, declare, rf, user
    ):
        declare("tests.kinds.Notes")
        request = rf.get(reverse("account-center"))
        request.user = user

        entries = [
            child
            for child in AccountCenterMenu.process(request).children
            if child.name == "personal-data"
        ]

        assert [entry.url for entry in entries] == [personal_data_address()]

    def test_the_route_takes_no_argument(self, declare, user):
        declare("tests.kinds.Notes")

        with pytest.raises(NoReverseMatch):
            reverse("mvp_compliance:personal-data", args=[user.pk])

    def test_an_anonymous_get_goes_to_sign_in_and_collects_nothing(
        self, declare, client, collects
    ):
        declare("tests.kinds.Notes")

        response = client.get(personal_data_address())

        assert response.status_code == 302
        assert response["Location"].startswith(reverse("account_login"))
        assert not any(mock.called for mock in collects)

    def test_an_anonymous_post_goes_to_sign_in_and_collects_nothing(
        self, declare, client, collects
    ):
        declare("tests.kinds.Notes")

        response = client.post(personal_data_address())

        assert response.status_code == 302
        assert response["Location"].startswith(reverse("account_login"))
        assert not any(mock.called for mock in collects)

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_a_person_who_has_not_confirmed_is_sent_to_confirm_and_nothing_is_collected(
        self, declare, client, user, collects, method
    ):
        declare("tests.kinds.Notes")
        client.force_login(user)

        response = getattr(client, method)(personal_data_address())

        assert response.status_code == 302
        assert response["Location"].startswith(reverse("account_reauthenticate"))
        assert not any(mock.called for mock in collects)

    def test_after_confirming_it_lists_every_kind_in_order_then_the_agreements(
        self, declare, client, user, collects
    ):
        declare("tests.kinds.Custom", "tests.kinds.Notes")
        client.force_login(user)
        confirm(client)

        response = client.get(personal_data_address())

        assert response.status_code == 200
        assert listed_kinds(response) == ["custom", "notes", "agreements"]
        assert not any(mock.called for mock in collects)

    def test_an_empty_declaration_lists_only_the_agreements(
        self, declare, client, user
    ):
        declare()
        client.force_login(user)
        confirm(client)

        response = client.get(personal_data_address())

        assert response.status_code == 200
        assert listed_kinds(response) == ["agreements"]

    def test_an_account_with_no_password_reaches_the_page_without_confirming(
        self, declare, client, user
    ):
        declare("tests.kinds.Notes")
        user.set_unusable_password()
        user.save()
        client.force_login(user)

        response = client.get(personal_data_address())

        assert response.status_code == 200

    def test_with_allauth_account_not_installed_the_page_is_not_found(
        self, declare, client, user, collects
    ):
        declare("tests.kinds.Notes")
        client.force_login(user)
        confirm(client)

        with patch.object(
            apps, "is_installed", side_effect=lambda name: name != "allauth.account"
        ):
            response = client.get(personal_data_address())

        assert response.status_code == 404
        assert not any(mock.called for mock in collects)


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_package_only")
class TestPersonalDataPageWithoutTheAccountArea:
    """A project that mounts no account area has no page, whoever asks."""

    def test_the_page_is_not_found_for_a_confirmed_person(
        self, declare, client, user, collects
    ):
        declare("tests.kinds.Notes")
        client.force_login(user)
        confirm(client)

        response = client.get(personal_data_address())

        assert response.status_code == 404
        assert not any(mock.called for mock in collects)

    def test_the_page_is_not_found_for_an_anonymous_visitor(self, declare, client):
        declare("tests.kinds.Notes")

        assert client.get(personal_data_address()).status_code == 404


@pytest.fixture
def downloaded(declare, client, user, stored_files):
    """Download a copy as a confirmed person holding a note with a file."""
    declare("tests.kinds.Notes")
    note = NoteFactory(
        owner=user, title="Heron", attachment=ContentFile(b"bytes", name="heron.txt")
    )
    client.force_login(user)
    confirm(client)
    opened = []
    spooled = tempfile.SpooledTemporaryFile

    def spool(*args, **kwargs):
        opened.append(spooled(*args, **kwargs))
        return opened[-1]

    with patch("mvp_compliance.views.tempfile.SpooledTemporaryFile", side_effect=spool):
        response = client.post(personal_data_address())
    archive = zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))
    response.close()
    return {"response": response, "stream": opened[0], "archive": archive, "note": note}


@pytest.mark.django_db
class TestPersonalDataDownload:
    """US-1 scenarios 5 and 11, FR-004, FR-008, FR-015, SC-006."""

    def test_it_answers_with_a_zip_attachment_named_for_the_day(self, downloaded):
        response = downloaded["response"]

        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        today = timezone.localdate()
        assert response["Content-Disposition"] == (
            f'attachment; filename="copy-of-your-data-{today:%Y-%m-%d}.zip"'
        )

    def test_the_zip_holds_the_page_the_data_and_the_file_with_its_bytes(
        self, downloaded
    ):
        archive = downloaded["archive"]
        path = f"files/notes/{downloaded['note'].pk}/attachment/heron.txt"

        assert set(archive.namelist()) == {"index.html", "data.json", path}
        assert archive.read(path) == b"bytes"

    def test_the_streamed_file_is_closed_when_the_response_is(self, downloaded):
        assert downloaded["stream"].closed

    def test_it_stores_nothing(self, declare, client, user, stored_files):
        declare("tests.kinds.Notes")
        NoteFactory(owner=user, attachment=ContentFile(b"bytes", name="heron.txt"))
        client.force_login(user)
        confirm(client)
        before = sorted(path for path in stored_files.rglob("*"))
        rows = (Note.objects.count(), Acceptance.objects.count())

        response = client.post(personal_data_address())
        b"".join(response.streaming_content)
        response.close()

        assert sorted(path for path in stored_files.rglob("*")) == before
        assert (Note.objects.count(), Acceptance.objects.count()) == rows


@pytest.mark.django_db
class TestPersonalDataCopyFails:
    """US-1 scenario 10, FR-018, FR-019: a copy that cannot be made is not handed over."""

    @pytest.fixture
    def attempt(self, declare, client, user, stored_files, caplog):
        """Ask for a copy while ``path`` is declared and ``damage`` has been done."""
        opened = []
        spooled = tempfile.SpooledTemporaryFile

        def spool(*args, **kwargs):
            opened.append(spooled(*args, **kwargs))
            return opened[-1]

        def ask(path, damage=lambda: None):
            declare(path)
            note = NoteFactory(
                owner=user, attachment=ContentFile(b"bytes", name="heron.txt")
            )
            damage_done = damage(note)
            client.force_login(user)
            confirm(client)
            with (
                caplog.at_level(logging.ERROR, logger="mvp_compliance.views"),
                patch(
                    "mvp_compliance.views.tempfile.SpooledTemporaryFile",
                    side_effect=spool,
                ),
            ):
                response = client.post(personal_data_address())
            return {
                "response": response,
                "opened": opened,
                "records": [
                    r
                    for r in caplog.records
                    if r.name == "mvp_compliance.views" and r.levelno == logging.ERROR
                ],
                "damage": damage_done,
            }

        return ask

    @staticmethod
    def lose_the_file(note):
        note.attachment.storage.delete(note.attachment.name)

    @pytest.fixture(
        params=[
            ("tests.kinds.Failing", None, RuntimeError),
            ("tests.kinds.Notes", "lose_the_file", FileNotFoundError),
            ("tests.kinds.BrokenTemplate", None, NoReverseMatch),
            ("tests.kinds.Undumpable", None, TypeError),
        ],
        ids=["collect", "file", "template", "data"],
    )
    def failure(self, request, attempt):
        path, damage, original = request.param
        damage = getattr(self, damage) if damage else (lambda note: None)
        return path, original, attempt(path, damage)

    def test_it_answers_500_with_no_attachment(self, failure):
        _path, _original, result = failure

        assert result["response"].status_code == 500
        assert not result["response"].has_header("Content-Disposition")

    def test_it_draws_the_page_with_the_failure_alert(self, failure):
        _path, _original, result = failure

        response = result["response"]
        assert "data-copy-failed" in response.content.decode()
        assert response.context["failed"] is True

    def test_it_logs_an_error_naming_the_kind_with_the_original_attached(self, failure):
        path, original, result = failure

        (record,) = result["records"]
        assert path in record.getMessage()
        assert isinstance(record.exc_info[1], PersonalDataError)
        assert isinstance(record.exc_info[1].__cause__, original)

    def test_it_keeps_no_temporary_file_open(self, failure):
        _path, _original, result = failure

        assert all(file.closed for file in result["opened"])


@pytest.mark.django_db
class TestPersonalDataCopiedSignal:
    """US-3, FR-025, FR-026: the project is told each time a copy is handed over."""

    @pytest.fixture
    def received(self):
        calls = []

        def receiver(sender, **kwargs):
            calls.append(kwargs)

        personal_data_copied.connect(receiver)
        yield calls
        personal_data_copied.disconnect(receiver)

    def test_it_is_sent_once_naming_the_person_and_the_kinds(
        self, declare, client, user, received
    ):
        declare("tests.kinds.Notes")
        client.force_login(user)
        confirm(client)

        response = client.post(personal_data_address())

        assert response.status_code == 200
        assert len(received) == 1
        assert received[0]["user"] == user
        assert received[0]["kinds"] == ["notes", "agreements"]

    def test_it_is_not_sent_when_the_copy_cannot_be_made(
        self, declare, client, user, received
    ):
        declare("tests.kinds.Failing")
        client.force_login(user)
        confirm(client)

        response = client.post(personal_data_address())

        assert response.status_code == 500
        assert received == []

    def test_a_failing_receiver_does_not_stop_the_download(
        self, declare, client, user, caplog
    ):
        def receiver(sender, **kwargs):
            raise RuntimeError("the project's own code failed")

        declare("tests.kinds.Notes")
        client.force_login(user)
        confirm(client)
        personal_data_copied.connect(receiver)
        try:
            response = client.post(personal_data_address())
        finally:
            personal_data_copied.disconnect(receiver)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        failure = next(
            record for record in caplog.records if record.name == "mvp_compliance.views"
        )
        assert failure.levelname == "ERROR"
        assert isinstance(failure.exc_info[1], RuntimeError)


def delete_address():
    return reverse("mvp_compliance:delete-account")


@pytest.fixture
def erasing():
    """Every ``erase`` the declared test kinds have, replaced by a recording mock."""
    with (
        patch.object(PersonalData, "erase") as base,
        patch("tests.kinds.Erases.erase") as own,
    ):
        yield [base, own]


@pytest.mark.django_db
class TestDeleteAccountPage:
    """US-1 scenarios 1 to 5, FR-001 to FR-006, FR-008, FR-018."""

    def test_without_a_declaration_the_route_does_not_exist_and_no_menu_entry_leads_to_it(
        self, rf, user
    ):
        request = rf.get(reverse("account-center"))
        request.user = user

        with pytest.raises(NoReverseMatch):
            delete_address()
        assert "delete-account" not in [
            child.name for child in AccountCenterMenu.process(request).children
        ]

    @pytest.mark.parametrize(
        "paths",
        [
            ["tests.kinds.Notes"],
            ["tests.kinds.DeletesNotes", "tests.kinds.Notes"],
        ],
        ids=["silent", "mixed"],
    )
    def test_while_a_kind_says_nothing_there_is_no_route_and_no_menu_entry(
        self, declare, rf, user, paths
    ):
        declare(*paths)
        request = rf.get(reverse("account-center"))
        request.user = user

        with pytest.raises(NoReverseMatch):
            delete_address()
        assert "delete-account" not in [
            child.name for child in AccountCenterMenu.process(request).children
        ]

    def test_when_every_kind_says_how_the_route_resolves_and_the_menu_leads_to_it(
        self, declare, rf, user
    ):
        declare("tests.kinds.DeletesNotes", "tests.kinds.WithAccount")
        request = rf.get(reverse("account-center"))
        request.user = user

        entries = [
            child
            for child in AccountCenterMenu.process(request).children
            if child.name == "delete-account"
        ]

        assert [entry.url for entry in entries] == [delete_address()]

    def test_the_route_takes_no_argument(self, declare, user):
        declare("tests.kinds.DeletesNotes")

        with pytest.raises(NoReverseMatch):
            reverse("mvp_compliance:delete-account", args=[user.pk])

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_an_anonymous_request_goes_to_sign_in_and_deletes_nothing(
        self, declare, client, user, erasing, method
    ):
        declare("tests.kinds.Erases")

        response = getattr(client, method)(delete_address())

        assert response.status_code == 302
        assert response["Location"].startswith(reverse("account_login"))
        assert type(user).objects.filter(pk=user.pk).exists()
        assert not any(mock.called for mock in erasing)

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_a_person_who_has_not_confirmed_is_sent_to_confirm_and_nothing_is_deleted(
        self, declare, client, user, erasing, method
    ):
        declare("tests.kinds.Erases")
        client.force_login(user)

        response = getattr(client, method)(delete_address())

        assert response.status_code == 302
        assert response["Location"].startswith(reverse("account_reauthenticate"))
        assert type(user).objects.filter(pk=user.pk).exists()
        assert not any(mock.called for mock in erasing)

    def test_after_confirming_it_lists_the_account_then_every_kind_in_order(
        self, declare, client, user, erasing
    ):
        declare("tests.kinds.WithAccount", "tests.kinds.DeletesNotes")
        client.force_login(user)
        confirm(client)

        response = client.get(delete_address())

        assert response.status_code == 200
        assert listed_kinds(response) == ["account", "withaccount", "deletesnotes"]
        assert type(user).objects.filter(pk=user.pk).exists()
        assert not any(mock.called for mock in erasing)

    def test_the_agreements_are_kept_by_default(self, declare, client, user):
        declare("tests.kinds.DeletesNotes")
        client.force_login(user)
        confirm(client)

        response = client.get(delete_address())

        assert 'data-kept="agreements"' in response.content.decode()
        assert "agreements" not in listed_kinds(response)

    def test_the_agreements_are_listed_as_deleted_when_they_do_not_survive(
        self, declare, client, user, settings
    ):
        settings.MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL = False
        declare("tests.kinds.DeletesNotes")
        client.force_login(user)
        confirm(client)

        response = client.get(delete_address())

        assert 'data-kept="' not in response.content.decode()
        assert listed_kinds(response) == ["account", "deletesnotes", "agreements"]

    def test_the_link_to_the_copy_is_present(self, declare, client, user):
        declare("tests.kinds.DeletesNotes")
        client.force_login(user)
        confirm(client)

        response = client.get(delete_address())

        assert response.context["copy_url"] == personal_data_address()
        assert personal_data_address() in response.content.decode()

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_an_account_with_no_password_reaches_the_page_without_confirming(
        self, declare, client, user, method
    ):
        declare("tests.kinds.DeletesNotes")
        user.set_unusable_password()
        user.save()
        client.force_login(user)

        response = getattr(client, method)(delete_address())

        assert response.status_code == 200

    def test_with_allauth_account_not_installed_the_page_is_not_found(
        self, declare, client, user, erasing
    ):
        declare("tests.kinds.Erases")
        client.force_login(user)
        confirm(client)

        with patch.object(
            apps, "is_installed", side_effect=lambda name: name != "allauth.account"
        ):
            response = client.get(delete_address())

        assert response.status_code == 404
        assert not any(mock.called for mock in erasing)


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_package_only")
class TestDeleteAccountPageWithoutTheAccountArea:
    """A project that mounts no account area has no page, whoever asks."""

    def test_the_page_is_not_found_for_a_confirmed_person(
        self, declare, client, user, erasing
    ):
        declare("tests.kinds.Erases")
        client.force_login(user)
        confirm(client)

        response = client.get(delete_address())

        assert response.status_code == 404
        assert not any(mock.called for mock in erasing)

    def test_the_page_is_not_found_for_an_anonymous_visitor(self, declare, client):
        declare("tests.kinds.Erases")

        assert client.get(delete_address()).status_code == 404
