"""Tests for mvp_compliance.emails."""

import re

import pytest
from django.conf import settings
from django.contrib import admin
from django.core import mail
from django.test import override_settings
from django.urls import path
from django.utils import translation

from mvp_compliance.emails import render_publication_email
from tests.factories import DocumentFactory, UserFactory, VersionFactory
from tests.test_admin import PACKAGE_DIR, catalog_entries

urlpatterns = [path("admin/", admin.site.urls)]

SITE_URL = "https://example.com"

EMAIL_TEMPLATES = PACKAGE_DIR / "templates" / "mvp_compliance" / "email"
TRANSLATE_TAG_RE = re.compile(r'{%\s*(?:translate|trans)\s+(["\'])((?:(?!\1).)*)\1')
BLOCKTRANSLATE_RE = re.compile(
    r"{%\s*blocktranslate[^%]*%}(.*?){%\s*endblocktranslate\s*%}", re.DOTALL
)
VARIABLE_RE = re.compile(r"{{\s*(\w+)\s*}}")


def email_template_strings() -> set[str]:
    """Every translatable string in the two email templates, as a catalog msgid.

    A ``blocktranslate`` body is turned into the msgid ``makemessages`` writes
    for it, each ``{{ name }}`` becoming ``%(name)s``.
    """
    strings: set[str] = set()
    for path_ in EMAIL_TEMPLATES.glob("*.txt"):
        text = path_.read_text(encoding="utf-8")
        strings.update(match.group(2) for match in TRANSLATE_TAG_RE.finditer(text))
        for block in BLOCKTRANSLATE_RE.findall(text):
            strings.add(VARIABLE_RE.sub(r"%(\1)s", block))
    return strings


def publish_two(publisher=None, name="Terms of service"):
    """Publish a document's first version, then a second, returning both."""
    document = DocumentFactory(name=name)
    first = VersionFactory(document=document, markdown="First wording")
    first.publish()
    second = VersionFactory(document=document, markdown="Second wording")
    second.publish(publisher=publisher)
    first.refresh_from_db()
    return first, second


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestRenderPublicationEmail:
    """The ready-made announcement renders text and sends nothing (FR-007, FR-015 to FR-018)."""

    def test_returns_a_subject_and_a_body_and_sends_nothing(self) -> None:
        """Scenario 1, FR-015, FR-007."""
        replaced, version = publish_two(publisher=UserFactory())

        result = render_publication_email(version, replaced, SITE_URL)

        subject, body = result
        assert isinstance(subject, str)
        assert isinstance(body, str)
        assert mail.outbox == []

    def test_the_body_names_the_document_the_versions_and_the_publisher(self) -> None:
        """Scenarios 2, 3, FR-016."""
        publisher = UserFactory(username="ada")
        replaced, version = publish_two(publisher=publisher)

        subject, body = render_publication_email(version, replaced, SITE_URL)

        assert "Terms of service" in subject
        assert "Terms of service" in body
        assert f"Version {version.number} of" in body
        assert f"replaces version {replaced.number}" in body
        assert "ada" in body
        assert version.published_at.strftime("%Y") in body

    def test_a_first_publication_says_it_is_the_first_version_in_force(self) -> None:
        """Scenario 4, FR-016."""
        version = VersionFactory()
        version.publish()

        _subject, body = render_publication_email(version, None, SITE_URL)

        assert "first version" in body
        assert "replaces" not in body.lower()

    def test_a_version_with_no_publisher_says_none_was_recorded(self) -> None:
        """Scenario 5, edge case: publisher with no name or email."""
        replaced, version = publish_two(publisher=None)

        _subject, body = render_publication_email(version, replaced, SITE_URL)

        assert version.publisher_display in body
        assert "Unknown publisher" in body

    def test_the_body_carries_the_site_address_and_the_admin_page_for_the_version(
        self,
    ) -> None:
        """FR-017, decisions.md D3."""
        replaced, version = publish_two()

        _subject, body = render_publication_email(
            version, replaced, "https://example.com/"
        )

        assert (
            f"https://example.com/admin/mvp_compliance/version/{version.pk}/change/"
            in body
        )

    def test_a_name_with_a_line_break_and_markup_gives_a_one_line_subject(
        self,
    ) -> None:
        """Scenario 8, FR-019, SC-007, edge case."""
        name = 'Terms\r\nBcc: x@example.com <b>&"of" use</b>'
        replaced, version = publish_two(name=name)

        subject, body = render_publication_email(version, replaced, SITE_URL)

        assert "\n" not in subject
        assert "\r" not in subject
        assert 'Terms Bcc: x@example.com <b>&"of" use</b>' in subject
        assert name in body
        assert "&lt;" not in subject + body
        assert "&amp;" not in subject + body

    def test_a_project_template_at_the_same_path_replaces_the_packages(
        self, tmp_path
    ) -> None:
        """Scenario 6, FR-021."""
        directory = tmp_path / "mvp_compliance" / "email"
        directory.mkdir(parents=True)
        (directory / "version_published_subject.txt").write_text(
            "Ours: {{ version.document.name }}"
        )
        (directory / "version_published_body.txt").write_text(
            "Ours: {{ version.publisher_display }} at {{ admin_url }}"
        )
        templates = [{**settings.TEMPLATES[0], "DIRS": [tmp_path]}]
        replaced, version = publish_two()

        with override_settings(TEMPLATES=templates):
            subject, body = render_publication_email(version, replaced, SITE_URL)

        assert subject == "Ours: Terms of service"
        assert body.startswith("Ours: Unknown publisher at https://example.com/")

    def test_the_subject_and_body_render_in_the_active_language(self) -> None:
        """Scenario 7, FR-020."""
        replaced, version = publish_two(publisher=UserFactory(username="ada"))

        with translation.override("de"):
            subject, body = render_publication_email(version, replaced, SITE_URL)

        assert (
            subject == f"Terms of service: Version {version.number} ist jetzt in Kraft"
        )
        assert (
            f'Version {version.number} von "Terms of service" ist jetzt in Kraft.'
            in body
        )
        assert "Veröffentlicht von: ada" in body
        assert f"Sie ersetzt Version {replaced.number}." in body
        assert "Im Admin ansehen: https://example.com/admin/" in body


class TestEmailCatalog:
    """SC-008: every string in the email templates is in the shipped English catalog."""

    def test_every_email_string_is_in_the_english_catalog(self) -> None:
        template_strings = email_template_strings()
        assert len(template_strings) >= 6

        # catalog_entries() reads the file as written, so a quote is still escaped.
        catalog_msgids = {
            msgid.replace('\\"', '"') for msgid, _msgstr in catalog_entries() if msgid
        }

        assert template_strings - catalog_msgids == set()
