"""The admin registration: the editor reaches its pages, and the changelist reads clearly.

Exercised through the ``client`` fixture against a real, permitted user — a ``ModelAdmin`` method
called directly proves nothing about what a request receives. ``urlpatterns`` below mounts the
admin for this module only (``@pytest.mark.urls(__name__)``); the shared ``tests/urls.py`` stays
empty because this package serves no address of its own.
"""

import ast
import re
from pathlib import Path

import pytest
from django.contrib import admin
from django.test import override_settings
from django.urls import path, reverse

import mvp_compliance
from mvp_compliance.models import Version
from mvp_compliance.rendering import get_renderer
from mvp_compliance.widgets import MarkdownEditorWidget
from tests.factories import VersionFactory

urlpatterns = [path("admin/", admin.site.urls)]

PACKAGE_DIR = Path(mvp_compliance.__file__).parent
CATALOG_PATH = PACKAGE_DIR / "locale" / "en" / "LC_MESSAGES" / "django.po"

#: Matches one ``msgid``/``msgstr`` pair, each possibly split across several
#: quoted continuation lines the way ``makemessages`` wraps a long string.
PO_ENTRY_RE = re.compile(
    r'^msgid((?:\s*"(?:[^"\\]|\\.)*")+)\s*\n^msgstr((?:\s*"(?:[^"\\]|\\.)*")+)',
    re.MULTILINE,
)
PO_LINE_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def catalog_entries() -> list[tuple[str, str]]:
    """Every ``(msgid, msgstr)`` pair in the shipped English catalog.

    Parsed straight from the ``.po`` file rather than kept as a second,
    hand-maintained list — a string added anywhere in the package is swept
    without anyone remembering to list it here (T049a, T049b).
    """
    text = CATALOG_PATH.read_text(encoding="utf-8")
    entries = []
    for msgid_block, msgstr_block in PO_ENTRY_RE.findall(text):
        msgid = "".join(PO_LINE_RE.findall(msgid_block))
        msgstr = "".join(PO_LINE_RE.findall(msgstr_block))
        entries.append((msgid, msgstr))
    return entries


def python_translatable_strings() -> set[str]:
    """Every string literal passed to ``_``/``gettext_lazy``/``gettext`` in the package."""
    strings: set[str] = set()
    for path_ in PACKAGE_DIR.rglob("*.py"):
        if "migrations" in path_.parts or "vendor" in path_.parts:
            continue
        tree = ast.parse(path_.read_text(encoding="utf-8"), filename=str(path_))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name not in ("_", "gettext_lazy", "gettext"):
                continue
            if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                strings.add(node.args[0].value)
    return strings


TEMPLATE_TAG_RE = re.compile(r'{%\s*(?:translate|trans)\s+(["\'])((?:(?!\1).)*)\1')


def template_translatable_strings() -> set[str]:
    """Every ``{% translate %}``/``{% trans %}`` string literal in the package's templates."""
    strings: set[str] = set()
    for path_ in PACKAGE_DIR.rglob("*.html"):
        if "vendor" in path_.parts:
            continue
        for match in TEMPLATE_TAG_RE.finditer(path_.read_text(encoding="utf-8")):
            strings.add(match.group(2))
    return strings


#: Every address this feature serves, and how to reach one given a draft to
#: address it with.
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
    "version publish": lambda draft: reverse(
        "admin:mvp_compliance_version_publish", args=[draft.pk]
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

    def test_what_was_previewed_is_what_publication_stores(
        self, client, editor, draft
    ) -> None:
        """T034, SC-004, US-3 scenario 2."""
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_preview", args=[draft.pk])
        )
        content = response.content.decode()
        match = re.search(
            r'<div id="mvp-compliance-preview-content">(.*?)</div>',
            content,
            re.DOTALL,
        )
        previewed_html = match.group(1)

        draft.publish()

        assert draft.html == previewed_html

    def test_the_change_form_offers_the_preview(self, client, editor, draft) -> None:
        """T035: any version the caller may view offers a way to its preview."""
        client.force_login(editor)
        preview_url = reverse("admin:mvp_compliance_version_preview", args=[draft.pk])

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk])
        )

        assert response.status_code == 200
        assert preview_url.encode() in response.content


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestPublish:
    """FR-013 to FR-020, SC-005 to SC-008, US-4 scenarios 1-8: publishing is
    deliberate, confirmed, and the one act in the package there is no way
    back from.
    """

    def test_a_caller_without_publish_version_is_refused_both_verbs(
        self, client, editor, draft
    ) -> None:
        """T040, FR-014, US-4 scenario 1."""
        client.force_login(editor)
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[draft.pk])

        get_response = client.get(publish_url)
        post_response = client.post(publish_url)

        draft.refresh_from_db()
        assert get_response.status_code == 403
        assert post_response.status_code == 403
        assert draft.status == draft.Status.DRAFT

    def test_a_caller_with_publish_version_reaches_the_publish_address(
        self, client, publisher, draft
    ) -> None:
        """T040, FR-014, US-4 scenario 1."""
        client.force_login(publisher)
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[draft.pk])

        response = client.get(publish_url)

        assert response.status_code == 200

    def test_a_get_confirms_and_publishes_nothing(
        self, client, publisher, draft
    ) -> None:
        """T042, FR-015, US-4 scenario 2."""
        client.force_login(publisher)
        expected_html = get_renderer()().render(draft.markdown)
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[draft.pk])

        response = client.get(publish_url)

        draft.refresh_from_db()
        content = response.content.decode()
        assert response.status_code == 200
        assert str(draft.document) in content
        assert str(draft.number) in content
        assert expected_html in content
        assert "cannot be changed" in content
        assert "another version" in content
        assert draft.status == draft.Status.DRAFT

    def test_a_post_publishes_and_declining_does_not(
        self, client, publisher, document
    ) -> None:
        """T044, FR-016, US-4 scenario 3."""
        client.force_login(publisher)
        previous = VersionFactory(document=document)
        previous.publish()
        draft = VersionFactory(document=document)
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[draft.pk])

        # Declining is the absence of a POST: reading the confirmation and
        # following its back link is a GET, and nothing is written.
        client.get(publish_url)
        draft.refresh_from_db()
        assert draft.status == draft.Status.DRAFT

        response = client.post(publish_url)

        draft.refresh_from_db()
        previous.refresh_from_db()
        assert response.status_code == 302
        assert draft.status == draft.Status.CURRENT
        assert draft.published_at is not None
        assert previous.status == previous.Status.SUPERSEDED

    def test_both_refusals_reach_the_author_as_a_message(
        self, client, publisher, document
    ) -> None:
        """T046, FR-018, SC-007."""
        client.force_login(publisher)
        empty_draft = VersionFactory(document=document, markdown="   \n\n   ")
        published = VersionFactory(document=document)
        published.publish()

        empty_response = client.post(
            reverse("admin:mvp_compliance_version_publish", args=[empty_draft.pk]),
            follow=True,
        )
        already_response = client.post(
            reverse("admin:mvp_compliance_version_publish", args=[published.pk]),
            follow=True,
        )

        empty_draft.refresh_from_db()
        published.refresh_from_db()
        assert b"Publishing this would produce no output" in empty_response.content
        assert b"This version has already been published" in already_response.content
        assert empty_draft.status == empty_draft.Status.DRAFT
        assert published.status == published.Status.CURRENT

    def test_saving_a_draft_publishes_nothing(self, client, editor, draft) -> None:
        """T047, FR-013, US-4 scenario 4."""
        client.force_login(editor)
        change_url = reverse("admin:mvp_compliance_version_change", args=[draft.pk])

        get_response = client.get(change_url)
        post_response = client.post(
            change_url,
            data={"document": draft.document_id, "markdown": "Updated wording"},
        )

        draft.refresh_from_db()
        changelist_response = client.get(
            reverse("admin:mvp_compliance_version_changelist")
        )
        assert post_response.status_code == 302
        assert draft.status == draft.Status.DRAFT
        assert draft.published_at is None
        assert b'name="publish"' not in get_response.content
        assert b'value="publish"' not in get_response.content
        assert b'value="publish"' not in changelist_response.content

    def test_a_published_version_has_no_editable_form(
        self, client, editor, published_version
    ) -> None:
        """T048, FR-017, SC-006, US-4 scenario 5."""
        client.force_login(editor)
        change_url = reverse(
            "admin:mvp_compliance_version_change", args=[published_version.pk]
        )

        response = client.get(change_url)

        content = response.content.decode()
        assert response.status_code == 200
        assert published_version.markdown in content
        assert 'name="markdown"' not in content
        assert "<textarea" not in content
        assert 'name="_save"' not in content

    def test_the_change_form_offers_a_publish_link_when_permitted(
        self, client, publisher, draft
    ) -> None:
        """The confirmation page needs a route to it (FR-013) — the same
        object-tools pattern T035 used for the preview link.
        """
        client.force_login(publisher)
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[draft.pk])

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk])
        )

        assert response.status_code == 200
        assert publish_url.encode() in response.content

    def test_the_change_form_offers_no_publish_link_without_permission(
        self, client, editor, draft
    ) -> None:
        client.force_login(editor)
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[draft.pk])

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk])
        )

        assert response.status_code == 200
        assert publish_url.encode() not in response.content


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestDocumentAdmin:
    """FR-021, FR-022, US-5 scenarios 1-3: starting the next version from the
    one in force.
    """

    def test_starting_the_next_version_opens_with_the_current_wording(
        self, client, editor, document
    ) -> None:
        """T050, FR-021, US-5 scenario 1."""
        client.force_login(editor)
        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()
        add_url = reverse("admin:mvp_compliance_version_add")

        response = client.get(add_url, {"document": document.pk})

        assert response.status_code == 200
        assert current.markdown.encode() in response.content


class TestUserFacingStrings:
    """FR-019, FR-020, SC-008, US-4 scenario 8: nothing this feature shows a
    person claims compliance, and every string it shows is translatable.

    Both tests sweep the shipped catalog itself, never a hand-kept list of
    strings this test file maintains — a string added later is covered
    without anybody remembering to add it (D14-style, one walk).
    """

    def test_nothing_claims_compliance(self) -> None:
        """T049a, FR-019, SC-008, US-4 scenario 8."""
        entries = catalog_entries()
        shown_strings = [msgstr for msgid, msgstr in entries if msgid]
        assert shown_strings

        for text in shown_strings:
            lowered = text.lower()
            assert "compliant" not in lowered, text
            assert "complies" not in lowered, text

    def test_every_string_is_translatable(self) -> None:
        """T049b, FR-020, SC-008."""
        shipped_strings = (
            python_translatable_strings() | template_translatable_strings()
        )
        assert shipped_strings

        catalog_msgids = {msgid for msgid, _msgstr in catalog_entries() if msgid}
        missing = shipped_strings - catalog_msgids

        assert not missing
