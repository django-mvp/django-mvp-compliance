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
from django.contrib import admin, messages
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import NoReverseMatch, path, reverse
from django.utils import formats, timezone
from django.utils.html import escape

import mvp_compliance
from mvp_compliance.models import Acceptance, Document, Translation, Version
from mvp_compliance.records import PersonalRecord
from mvp_compliance.rendering import get_renderer
from mvp_compliance.widgets import MarkdownEditorWidget
from tests.conftest import grant
from tests.factories import (
    AcceptanceFactory,
    DocumentFactory,
    TranslationFactory,
    UserFactory,
    VersionFactory,
)

urlpatterns = [path("admin/", admin.site.urls)]

PACKAGE_DIR = Path(mvp_compliance.__file__).parent
CATALOG_PATH = PACKAGE_DIR / "locale" / "en" / "LC_MESSAGES" / "django.po"

#: Matches one ``msgid``/``msgstr`` pair, each possibly split across several
#: quoted continuation lines the way ``makemessages`` wraps a long string.
PO_ENTRY_RE = re.compile(
    r'^msgid((?:\s*"(?:[^"\\]|\\.)*")+)\s*\n^msgstr((?:\s*"(?:[^"\\]|\\.)*")+)',
    re.MULTILINE,
)
#: Matches a plural entry, whose ``msgid_plural`` sits between the ``msgid``
#: and its numbered ``msgstr`` lines.
PO_PLURAL_ENTRY_RE = re.compile(
    r'^msgid((?:\s*"(?:[^"\\]|\\.)*")+)\s*\n^msgid_plural((?:\s*"(?:[^"\\]|\\.)*")+)'
    r'\s*\n^msgstr\[0\]((?:\s*"(?:[^"\\]|\\.)*")+)\s*\n^msgstr\[1\]((?:\s*"(?:[^"\\]|\\.)*")+)',
    re.MULTILINE,
)
PO_LINE_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def catalog_entries() -> list[tuple[str, str]]:
    """Every ``(msgid, msgstr)`` pair in the shipped English catalog.

    Parsed straight from the ``.po`` file rather than kept as a second,
    hand-maintained list — a string added anywhere in the package is swept
    without anyone remembering to list it here.
    """
    text = CATALOG_PATH.read_text(encoding="utf-8")
    entries = []
    for msgid_block, msgstr_block in PO_ENTRY_RE.findall(text):
        msgid = "".join(PO_LINE_RE.findall(msgid_block))
        msgstr = "".join(PO_LINE_RE.findall(msgstr_block))
        entries.append((msgid, msgstr))
    # A plural entry carries two strings, each with its own translation.
    for blocks in PO_PLURAL_ENTRY_RE.findall(text):
        singular, plural, first, second = (
            "".join(PO_LINE_RE.findall(block)) for block in blocks
        )
        entries.extend([(singular, first), (plural, second)])
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


VERSION_CHANGE_URL_RE = re.compile(r"/admin/mvp_compliance/version/\d+/change/")

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
#: with a ``KeyError`` rather than being silently skipped.
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
    def test_the_add_page_carries_the_editor_widget(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_add"), {"document": document.pk}
        )

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
        assert str(Version.Status.CURRENT.label) in content

    def test_a_draft_is_labelled_draft_where_its_number_would_be(
        self, client, editor, draft, published_version
    ) -> None:
        client.force_login(editor)

        content = client.get(
            reverse("admin:mvp_compliance_version_changelist")
        ).content.decode()

        number_cells = re.findall(
            r'<td class="field-version_number">([^<]*)</td>', content
        )
        assert sorted(number_cells) == sorted([published_version.number, "Draft"])

    def test_a_version_in_forces_page_offers_the_next_version(
        self, client, editor, published_version
    ) -> None:
        client.force_login(editor)
        expected_url = (
            f"{reverse('admin:mvp_compliance_version_add')}"
            f"?document={published_version.document_id}"
        )

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[published_version.pk])
        )

        assert response.status_code == 200
        assert expected_url.encode() in response.content

    def test_a_draft_offers_no_control_to_start_the_next_version(
        self, client, editor, draft
    ) -> None:
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk])
        )

        assert response.status_code == 200
        add_url = f"{reverse('admin:mvp_compliance_version_add')}?document={draft.document_id}"
        assert add_url.encode() not in response.content

    def test_the_changelist_offers_a_filter_by_document(self, client, editor) -> None:
        # Django's filter shows nothing for a relation with one value, so two documents.
        client.force_login(editor)
        wanted = VersionFactory()
        VersionFactory()

        response = client.get(reverse("admin:mvp_compliance_version_changelist"))

        assert response.status_code == 200
        filter_link = f"?document__id__exact={wanted.document_id}"
        assert filter_link.encode() in response.content

    def test_narrowing_by_document_shows_only_that_documents_versions(
        self, client, editor
    ) -> None:
        client.force_login(editor)
        wanted = VersionFactory()
        other = VersionFactory()

        response = client.get(
            reverse("admin:mvp_compliance_version_changelist"),
            {"document__id__exact": wanted.document_id},
        )

        assert response.status_code == 200
        content = response.content.decode()
        assert str(wanted) in content
        assert str(other) not in content


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestAddingAVersion:
    def test_the_changelist_offers_no_way_to_add_a_version(
        self, client, editor
    ) -> None:
        client.force_login(editor)

        response = client.get(reverse("admin:mvp_compliance_version_changelist"))

        assert response.status_code == 200
        add_url = reverse("admin:mvp_compliance_version_add")
        assert add_url.encode() not in response.content

    def test_a_bare_request_for_the_add_form_is_refused(self, client, editor) -> None:
        client.force_login(editor)

        response = client.get(reverse("admin:mvp_compliance_version_add"))

        assert response.status_code == 403

    def test_reaching_the_add_form_from_a_document_still_works(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_add"), {"document": document.pk}
        )

        assert response.status_code == 200

    def test_the_add_form_offers_no_save_and_add_another(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_add"), {"document": document.pk}
        )

        assert response.status_code == 200
        assert b'name="_addanother"' not in response.content


class TestToolbarAgreesWithTheAllowList:
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
        client.force_login(editor)
        drafts = [VersionFactory(document=document) for _ in range(3)]

        changelist_content = client.get(
            reverse("admin:mvp_compliance_version_changelist")
        ).content.decode()
        for version in drafts:
            change_url = reverse(
                "admin:mvp_compliance_version_change", args=[version.pk]
            )
            assert change_url in changelist_content

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
    def test_editor_receives_the_rendering_of_the_drafts_markdown(
        self, client, editor, draft
    ) -> None:
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

    def test_the_preview_links_back_to_the_version(self, client, editor, draft) -> None:
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
    def test_a_caller_without_publish_version_is_refused_both_verbs(
        self, client, editor, draft
    ) -> None:
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
        client.force_login(publisher)
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[draft.pk])

        response = client.get(publish_url)

        assert response.status_code == 200

    def test_a_get_confirms_and_publishes_nothing(
        self, client, publisher, draft
    ) -> None:
        client.force_login(publisher)
        expected_html = get_renderer()().render(draft.markdown)
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[draft.pk])

        response = client.get(publish_url)

        draft.refresh_from_db()
        content = response.content.decode()
        assert response.status_code == 200
        assert str(draft) in content
        assert expected_html in content
        assert draft.status == draft.Status.DRAFT

    def test_a_post_publishes_and_declining_does_not(
        self, client, publisher, document
    ) -> None:
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
        for response in (empty_response, already_response):
            levels = [m.level for m in response.context["messages"]]
            assert levels == [messages.ERROR]
        assert empty_draft.status == empty_draft.Status.DRAFT
        assert published.status == published.Status.CURRENT

    def test_somebody_who_may_publish_and_may_not_write_can_publish(
        self, client, approver, draft
    ) -> None:
        client.force_login(approver)
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[draft.pk])

        confirmation = client.get(publish_url)
        published = client.post(publish_url)
        refused_write = client.post(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk]),
            data={
                "document": draft.document_id,
                "markdown": "Rewritten by the approver",
            },
        )

        draft.refresh_from_db()
        assert confirmation.status_code == 200
        assert published.status_code == 302
        assert draft.status == draft.Status.CURRENT
        assert refused_write.status_code == 403
        assert draft.markdown != "Rewritten by the approver"

    def test_the_confirmation_shows_a_published_versions_stored_output(
        self, client, publisher, published_version
    ) -> None:
        client.force_login(publisher)
        stored_html = published_version.html

        with override_settings(
            MVP_COMPLIANCE_RENDERER="tests.test_models.UppercaseRenderer"
        ):
            response = client.get(
                reverse(
                    "admin:mvp_compliance_version_publish", args=[published_version.pk]
                )
            )

        content = response.content.decode()
        assert response.status_code == 200
        assert stored_html in content
        assert stored_html.upper() not in content

    def test_a_duplicate_of_the_version_in_force_is_refused_readably(
        self, client, publisher, document
    ) -> None:
        client.force_login(publisher)
        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()
        duplicate = VersionFactory(document=document, markdown="The current wording")

        response = client.post(
            reverse("admin:mvp_compliance_version_publish", args=[duplicate.pk]),
            follow=True,
        )

        duplicate.refresh_from_db()
        levels = [m.level for m in response.context["messages"]]
        assert levels == [messages.ERROR]
        assert duplicate.status == duplicate.Status.DRAFT

    def test_saving_a_draft_publishes_nothing(self, client, editor, draft) -> None:
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
    def test_starting_the_next_version_opens_with_the_current_wording(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        current = VersionFactory(document=document, markdown="The current wording")
        current.publish()
        add_url = reverse("admin:mvp_compliance_version_add")

        response = client.get(add_url, {"document": document.pk})

        assert response.status_code == 200
        assert current.markdown.encode() in response.content

    def test_a_document_with_nothing_in_force_opens_empty(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        draft = VersionFactory(document=document, markdown="Unpublished wording")
        add_url = reverse("admin:mvp_compliance_version_add")

        response = client.get(add_url, {"document": document.pk})

        assert response.status_code == 200
        assert draft.markdown.encode() not in response.content

    @pytest.mark.parametrize(
        "document_id", ["not-a-number", "", "1 OR 1=1", "999999999"]
    )
    def test_a_document_the_query_string_cannot_name_is_refused(
        self, client, editor, document_id
    ) -> None:
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_add"), {"document": document_id}
        )

        assert response.status_code == 403

    def test_the_document_page_offers_its_current_version_and_history(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        current = VersionFactory(document=document, markdown="Current wording")
        current.publish()
        current_url = reverse("admin:mvp_compliance_version_change", args=[current.pk])
        history_url = (
            f"{reverse('admin:mvp_compliance_version_changelist')}"
            f"?document__id__exact={document.pk}"
        )
        add_url = (
            f"{reverse('admin:mvp_compliance_version_add')}?document={document.pk}"
        )

        response = client.get(
            reverse("admin:mvp_compliance_document_change", args=[document.pk])
        )

        assert response.status_code == 200
        content = response.content.decode()
        assert current_url in content
        assert history_url in content
        assert add_url not in content

    @pytest.mark.parametrize("with_draft", [False, True])
    def test_a_document_with_nothing_in_force_offers_no_current_version_control(
        self, client, editor, document, with_draft
    ) -> None:
        client.force_login(editor)
        if with_draft:
            VersionFactory(document=document, markdown="Unpublished wording")
        history_url = (
            f"{reverse('admin:mvp_compliance_version_changelist')}"
            f"?document__id__exact={document.pk}"
        )

        response = client.get(
            reverse("admin:mvp_compliance_document_change", args=[document.pk])
        )

        assert response.status_code == 200
        content = response.content.decode()
        assert history_url in content
        assert not VERSION_CHANGE_URL_RE.search(content)

    def test_editing_the_copy_leaves_the_published_version_alone(
        self, client, editor, document
    ) -> None:
        # Posted with the document in the query string, the way the add form's empty
        # action submits.
        client.force_login(editor)
        current = VersionFactory(document=document, markdown="Original wording")
        current.publish()
        original_markdown = current.markdown
        original_html = current.html
        add_url = reverse("admin:mvp_compliance_version_add")

        response = client.post(
            f"{add_url}?document={document.pk}",
            data={"document": document.pk, "markdown": "Rewritten wording"},
        )

        current.refresh_from_db()
        assert response.status_code == 302
        assert current.markdown == original_markdown
        assert current.html == original_html


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestDocumentSlugInTheAdmin:
    """US-4 scenarios 1-3, FR-016, FR-017: the slug follows the name until
    a version is published, and is shown fixed afterwards.
    """

    def test_the_add_form_prepopulates_the_slug_from_the_name(
        self, client, editor
    ) -> None:
        client.force_login(editor)

        response = client.get(reverse("admin:mvp_compliance_document_add"))

        assert response.status_code == 200
        assert response.context["adminform"].prepopulated_fields == [
            {
                "field": response.context["adminform"].form["slug"],
                "dependencies": [response.context["adminform"].form["name"]],
            }
        ]

    def test_an_unpublished_documents_slug_can_be_edited(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_change", args=[document.pk])

        page = client.get(url)
        response = client.post(
            url, {"name": document.name, "slug": "new-address", "kind": "agreed"}
        )

        assert 'name="slug"' in page.content.decode()
        assert response.status_code == 302
        document.refresh_from_db()
        assert document.slug == "new-address"

    def test_a_published_documents_slug_is_shown_read_only(
        self, client, editor, document
    ) -> None:
        VersionFactory(document=document).publish()
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_change", args=[document.pk])

        response = client.get(url)

        content = response.content.decode()
        assert response.status_code == 200
        assert 'name="slug"' not in content
        assert document.slug in content

    def test_a_post_carrying_a_different_slug_leaves_a_published_slug_alone(
        self, client, editor, document
    ) -> None:
        VersionFactory(document=document).publish()
        original = document.slug
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_change", args=[document.pk])

        response = client.post(
            url, {"name": "A new name", "slug": "new-address", "kind": "agreed"}
        )

        assert response.status_code == 302
        document.refresh_from_db()
        assert document.slug == original
        assert document.name == "A new name"

    def test_the_add_form_refuses_the_slug_of_the_list_of_agreed_documents(
        self, client, editor
    ) -> None:
        client.force_login(editor)

        response = client.post(
            reverse("admin:mvp_compliance_document_add"),
            {"name": "Agreed", "slug": "agreed", "kind": "agreed"},
        )

        assert response.status_code == 200
        assert "slug" in response.context["adminform"].form.errors
        assert not Document.objects.filter(slug="agreed").exists()

    def test_the_add_form_refuses_the_slug_of_the_page_that_asks(
        self, client, editor
    ) -> None:
        client.force_login(editor)

        response = client.post(
            reverse("admin:mvp_compliance_document_add"),
            {"name": "Agree", "slug": "agree", "kind": "agreed"},
        )

        assert response.status_code == 200
        assert "slug" in response.context["adminform"].form.errors
        assert not Document.objects.filter(slug="agree").exists()


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestDeclaredDocumentAdmin:
    """US-2 scenario 1, FR-011, FR-012: a declared document's slug is fixed in
    the admin before any version is published.
    """

    @pytest.fixture
    def declared(self, settings):
        settings.MVP_COMPLIANCE_DOCUMENTS = {"privacy-policy": "Privacy policy"}
        return Document.objects.create(name="Privacy policy", slug="privacy-policy")

    def test_the_change_form_has_no_slug_input(self, client, editor, declared) -> None:
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_change", args=[declared.pk])

        response = client.get(url)

        assert response.status_code == 200
        assert 'name="slug"' not in response.content.decode()

    def test_a_post_carrying_a_different_slug_leaves_the_slug_alone(
        self, client, editor, declared
    ) -> None:
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_change", args=[declared.pk])

        response = client.post(
            url,
            {
                "name": "Privacy",
                "slug": "new-address",
                "kind": Document.Kind.NOTICE,
            },
        )

        assert response.status_code == 302
        declared.refresh_from_db()
        assert declared.slug == "privacy-policy"
        assert declared.name == "Privacy"
        assert declared.kind == Document.Kind.NOTICE
        assert not declared.enforced

    def test_an_undeclared_document_without_a_version_still_has_the_input(
        self, client, editor, declared
    ) -> None:
        other = DocumentFactory()
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_change", args=[other.pk])

        response = client.get(url)

        assert 'name="slug"' in response.content.decode()


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestDocumentEnforcement:
    """US-2 scenarios 4-6, FR-014: enforcement is chosen on the form and shown in the list."""

    @staticmethod
    def held_about(document):
        """Every version and acceptance of ``document`` as plain rows."""
        versions = document.versions.order_by("pk").values_list(
            "pk", "number", "status", "markdown", "html", "published_at"
        )
        acceptances = Acceptance.objects.filter(version__document=document)
        return list(versions), list(
            acceptances.order_by("pk").values_list(
                "pk", "subject", "version_id", "accepted_at"
            )
        )

    def test_a_document_added_with_the_field_left_as_rendered_is_enforced(
        self, client, editor
    ) -> None:
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_add")

        preselected = client.get(url).context["adminform"].form["enforced"].value()
        data = {"name": "Terms", "slug": "terms", "kind": Document.Kind.AGREED}
        if preselected:
            data["enforced"] = "on"
        response = client.post(url, data)

        assert response.status_code == 302
        assert Document.objects.get(slug="terms").enforced

    def test_a_document_added_with_the_field_cleared_is_not_enforced(
        self, client, editor
    ) -> None:
        client.force_login(editor)

        response = client.post(
            reverse("admin:mvp_compliance_document_add"),
            {
                "name": "Cookie policy",
                "slug": "cookie-policy",
                "kind": Document.Kind.AGREED,
            },
        )

        assert response.status_code == 302
        assert not Document.objects.get(slug="cookie-policy").enforced

    def test_the_change_form_switches_enforcement_off_and_on_and_nothing_recorded_moves(
        self, client, editor, document
    ) -> None:
        for wording in ("First wording", "Second wording"):
            version = VersionFactory(document=document, markdown=wording)
            version.publish()
            AcceptanceFactory(version=version)
        before = self.held_about(document)
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_change", args=[document.pk])
        fields = {
            "name": document.name,
            "slug": document.slug,
            "kind": Document.Kind.AGREED,
        }

        off = client.post(url, fields)
        document.refresh_from_db()
        enforced_while_off = document.enforced
        held_while_off = self.held_about(document)
        on = client.post(url, {**fields, "enforced": "on"})
        document.refresh_from_db()

        assert off.status_code == 302
        assert on.status_code == 302
        assert not enforced_while_off
        assert document.enforced
        assert held_while_off == before
        assert self.held_about(document) == before
        assert len(before[0]) == 2
        assert len(before[1]) == 2

    def test_the_changelist_has_an_enforced_cell_on_the_row_of_each_document(
        self, client, editor
    ) -> None:
        DocumentFactory(name="Terms of use", enforced=True)
        DocumentFactory(name="Cookie policy", enforced=False)
        client.force_login(editor)

        content = client.get(
            reverse("admin:mvp_compliance_document_changelist")
        ).content.decode()

        rows = {
            name: row
            for row in content.split("<tr")
            for name in ("Terms of use", "Cookie policy")
            if name in row
        }
        cells = {
            name: re.search(r'<td class="field-enforced">(.*?)</td>', row, re.DOTALL)
            for name, row in rows.items()
        }
        assert set(cells) == {"Terms of use", "Cookie policy"}
        assert all(cells.values())
        assert cells["Terms of use"].group(1) != cells["Cookie policy"].group(1)


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestDocumentKindInTheAdmin:
    """US-2 scenarios 1-3, FR-009: the kind is visible in the list and chosen on the form."""

    def test_the_changelist_shows_each_documents_kind(self, client, editor) -> None:
        agreed = DocumentFactory()
        notice = DocumentFactory(kind=Document.Kind.NOTICE)
        client.force_login(editor)

        response = client.get(reverse("admin:mvp_compliance_document_changelist"))

        content = response.content.decode()
        assert response.status_code == 200
        assert f'field-kind">{agreed.get_kind_display()}<' in content
        assert f'field-kind">{notice.get_kind_display()}<' in content

    def test_a_document_added_without_touching_the_kind_is_one_people_agree_to(
        self, client, editor
    ) -> None:
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_add")

        preselected = client.get(url).context["adminform"].form["kind"].value()
        response = client.post(
            url, {"name": "Terms", "slug": "terms", "kind": preselected}
        )

        assert response.status_code == 302
        assert Document.objects.get(slug="terms").kind == Document.Kind.AGREED

    def test_a_document_added_as_a_notice_is_a_notice(self, client, editor) -> None:
        client.force_login(editor)

        response = client.post(
            reverse("admin:mvp_compliance_document_add"),
            {"name": "Impressum", "slug": "impressum", "kind": Document.Kind.NOTICE},
        )

        assert response.status_code == 302
        assert Document.objects.get(slug="impressum").kind == Document.Kind.NOTICE

    def test_the_change_form_changes_the_kind_of_a_document_with_published_versions(
        self, client, editor, document
    ) -> None:
        first = VersionFactory(document=document, markdown="First wording")
        first.publish()
        second = VersionFactory(document=document, markdown="Second wording")
        second.publish()
        before = list(
            document.versions.order_by("pk").values_list(
                "pk", "number", "status", "markdown", "html"
            )
        )
        client.force_login(editor)
        url = reverse("admin:mvp_compliance_document_change", args=[document.pk])

        response = client.post(
            url,
            {
                "name": document.name,
                "slug": document.slug,
                "kind": Document.Kind.NOTICE,
            },
        )

        assert response.status_code == 302
        document.refresh_from_db()
        assert document.kind == Document.Kind.NOTICE
        assert (
            list(
                document.versions.order_by("pk").values_list(
                    "pk", "number", "status", "markdown", "html"
                )
            )
            == before
        )


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestDisclosureRefusals:
    def test_the_page_is_the_only_address_the_proxy_serves(
        self, client, disclosure_producer
    ) -> None:
        # Django's change view loads the row before checking permissions, so these
        # addresses must not exist.
        acceptance = AcceptanceFactory(ip_address="203.0.113.9")
        client.force_login(disclosure_producer)

        for name in ("add", "change", "delete", "history"):
            with pytest.raises(NoReverseMatch):
                reverse(f"admin:mvp_compliance_disclosure_{name}", args=[acceptance.pk])

        page = reverse("admin:mvp_compliance_disclosure_changelist")
        for guessed in (f"{page}{acceptance.pk}/change/", f"{page}add/"):
            assert client.get(guessed).status_code == 404, guessed

    def test_not_signed_in_is_refused(self, client) -> None:
        response = client.get(reverse("admin:mvp_compliance_disclosure_changelist"))

        assert response.status_code == 302

    def test_signed_in_and_not_staff_is_refused(self, client, visitor) -> None:
        client.force_login(visitor)

        response = client.get(reverse("admin:mvp_compliance_disclosure_changelist"))

        assert response.status_code == 302

    def test_staff_holding_every_other_permission_is_refused(
        self, client, everything_else
    ) -> None:
        client.force_login(everything_else)

        response = client.get(reverse("admin:mvp_compliance_disclosure_changelist"))

        assert response.status_code == 403

    def test_a_refusal_reveals_nothing(self, client, everything_else) -> None:
        client.force_login(everything_else)
        with_records = AcceptanceFactory()
        url = reverse("admin:mvp_compliance_disclosure_changelist")

        has_records_response = client.get(url, {"subject": with_records.subject})
        no_records_response = client.get(
            url, {"subject": "nobody-the-package-has-ever-heard-of"}
        )

        assert has_records_response.status_code == 403
        assert no_records_response.status_code == 403
        assert has_records_response.content == no_records_response.content

    def test_the_permission_is_held_by_nobody_on_installation(self) -> None:
        fresh_account = UserFactory()
        fresh_staff = UserFactory(is_staff=True)

        assert not fresh_account.has_perm("mvp_compliance.produce_disclosure")
        assert not fresh_staff.has_perm("mvp_compliance.produce_disclosure")
        assert Permission.objects.filter(
            content_type__app_label="mvp_compliance",
            codename="produce_disclosure",
        ).exists()


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestDisclosurePage:
    def test_the_answer_names_every_acceptance_in_full(
        self, client, disclosure_producer
    ) -> None:
        client.force_login(disclosure_producer)
        someone = UserFactory()
        document = DocumentFactory(name="Privacy policy")
        version = VersionFactory(
            document=document, markdown="# Privacy policy\n\nSome wording."
        )
        version.publish()
        acceptance = AcceptanceFactory(user=someone, version=version)
        url = reverse("admin:mvp_compliance_disclosure_changelist")

        response = client.get(url, {"subject": someone.username})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Privacy policy" in content
        assert str(version.number) in content
        expected_moment = formats.date_format(
            timezone.localtime(acceptance.accepted_at), "DATETIME_FORMAT"
        )
        assert expected_moment in content
        assert version.html in content

    def test_a_reader_who_may_view_versions_sees_each_version_as_a_link(
        self, client, disclosure_producer
    ) -> None:
        grant(disclosure_producer, "view_version")
        client.force_login(disclosure_producer)
        someone = UserFactory()
        version = VersionFactory()
        version.publish()
        AcceptanceFactory(user=someone, version=version)
        url = reverse("admin:mvp_compliance_disclosure_changelist")
        change = reverse("admin:mvp_compliance_version_change", args=[version.pk])

        content = client.get(url, {"subject": someone.username}).content.decode()

        assert f'href="{change}"' in content

    def test_a_superuser_sees_each_version_as_a_link(self, client) -> None:
        client.force_login(UserFactory(is_staff=True, is_superuser=True))
        someone = UserFactory()
        version = VersionFactory()
        version.publish()
        AcceptanceFactory(user=someone, version=version)
        url = reverse("admin:mvp_compliance_disclosure_changelist")
        change = reverse("admin:mvp_compliance_version_change", args=[version.pk])

        content = client.get(url, {"subject": someone.username}).content.decode()

        assert f'href="{change}"' in content

    def test_a_reader_holding_produce_disclosure_alone_sees_plain_text(
        self, client, disclosure_producer
    ) -> None:
        client.force_login(disclosure_producer)
        someone = UserFactory()
        version = VersionFactory()
        version.publish()
        AcceptanceFactory(user=someone, version=version)
        url = reverse("admin:mvp_compliance_disclosure_changelist")
        change = reverse("admin:mvp_compliance_version_change", args=[version.pk])

        response = client.get(url, {"subject": someone.username})

        assert response.status_code == 200
        assert change not in response.content.decode()
        assert str(version.number) in response.content.decode()

    def test_a_person_with_no_records_gets_a_page_saying_so(
        self, client, disclosure_producer
    ) -> None:
        client.force_login(disclosure_producer)
        url = reverse("admin:mvp_compliance_disclosure_changelist")

        response = client.get(url, {"subject": "nobody-the-package-has-ever-heard-of"})

        assert response.status_code == 200
        assert response.context["record"].is_empty

    def test_the_answer_carries_the_address_a_record_holds(
        self, client, disclosure_producer
    ) -> None:
        client.force_login(disclosure_producer)
        someone = UserFactory()
        with_address = VersionFactory()
        with_address.publish()
        without_address = VersionFactory()
        without_address.publish()
        AcceptanceFactory(user=someone, version=with_address, ip_address="198.51.100.7")
        AcceptanceFactory(user=someone, version=without_address)
        url = reverse("admin:mvp_compliance_disclosure_changelist")

        content = client.get(url, {"subject": someone.username}).content.decode()

        assert "198.51.100.7" in content

    def test_the_page_offers_no_way_to_change_anything(
        self, client, disclosure_producer, everything_else
    ) -> None:
        client.force_login(disclosure_producer)
        url = reverse("admin:mvp_compliance_disclosure_changelist")

        response = client.get(url)
        content = response.content.decode()

        assert response.status_code == 200
        assert "addlink" not in content
        assert "changelink" not in content
        assert "deletelink" not in content
        assert 'name="_save"' not in content

        index_response = client.get(reverse("admin:index"))
        assert url.encode() in index_response.content

        client.force_login(everything_else)
        everyone_elses_index = client.get(reverse("admin:index"))
        assert url.encode() not in everyone_elses_index.content

    def test_a_person_whose_account_is_gone(self, client, disclosure_producer) -> None:
        someone = UserFactory()
        document = DocumentFactory(name="Privacy policy")
        version = VersionFactory(
            document=document, markdown="# Privacy policy\n\nSome wording."
        )
        version.publish()
        acceptance = AcceptanceFactory(user=someone, version=version)
        subject = acceptance.subject
        someone.delete()

        client.force_login(disclosure_producer)
        url = reverse("admin:mvp_compliance_disclosure_changelist")

        response = client.get(url, {"subject": subject})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Privacy policy" in content
        assert str(version.number) in content
        expected_moment = formats.date_format(
            timezone.localtime(acceptance.accepted_at), "DATETIME_FORMAT"
        )
        assert expected_moment in content
        assert version.html in content

    def test_the_page_states_what_it_covers(self, client, disclosure_producer) -> None:
        client.force_login(disclosure_producer)
        someone = UserFactory()
        version = VersionFactory()
        version.publish()
        AcceptanceFactory(user=someone, version=version)
        url = reverse("admin:mvp_compliance_disclosure_changelist")
        statement = str(PersonalRecord(subject="irrelevant", sections=()).coverage)

        full_content = client.get(url, {"subject": someone.username}).content.decode()
        empty_content = client.get(
            url, {"subject": "nobody-the-package-has-ever-heard-of"}
        ).content.decode()

        assert statement in full_content
        assert statement in empty_content


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestDocumentChangelist:
    def test_a_document_with_nothing_in_force_reads_as_a_normal_state(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        changelist_url = reverse("admin:mvp_compliance_document_changelist")

        response = client.get(changelist_url)

        assert response.status_code == 200
        content = response.content.decode()
        assert not VERSION_CHANGE_URL_RE.search(content)
        assert 'field-published_version_count">0<' in content

    def test_a_draft_alone_still_reads_as_nothing_in_force(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        VersionFactory(document=document, markdown="Unpublished wording")
        changelist_url = reverse("admin:mvp_compliance_document_changelist")

        response = client.get(changelist_url)

        content = response.content.decode()
        assert not VERSION_CHANGE_URL_RE.search(content)
        assert 'field-published_version_count">0<' in content

    def test_the_version_in_force_links_to_its_own_page_and_shows_its_date(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        current = VersionFactory(document=document, markdown="Current wording")
        current.publish()
        version_url = reverse("admin:mvp_compliance_version_change", args=[current.pk])
        changelist_url = reverse("admin:mvp_compliance_document_changelist")

        response = client.get(changelist_url)

        content = response.content.decode()
        assert f'href="{version_url}"' in content
        assert current.number in content
        assert 'field-published_version_count">1<' in content

    def test_a_superseding_publish_keeps_the_count_moving_and_the_link_current(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        first = VersionFactory(document=document, markdown="First wording")
        first.publish()
        second = VersionFactory(document=document, markdown="Second wording")
        second.publish()
        second_url = reverse("admin:mvp_compliance_version_change", args=[second.pk])
        first_url = reverse("admin:mvp_compliance_version_change", args=[first.pk])
        changelist_url = reverse("admin:mvp_compliance_document_changelist")

        response = client.get(changelist_url)

        content = response.content.decode()
        assert f'href="{second_url}"' in content
        assert second.number in content
        assert first_url not in content
        assert 'field-published_version_count">2<' in content

    def test_a_draft_beside_a_version_in_force_is_not_counted(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        current = VersionFactory(document=document, markdown="Current wording")
        current.publish()
        VersionFactory(document=document, markdown="Unpublished rewording")
        changelist_url = reverse("admin:mvp_compliance_document_changelist")

        response = client.get(changelist_url)

        content = response.content.decode()
        assert 'field-published_version_count">1<' in content

    def test_the_changelist_costs_a_fixed_number_of_queries(
        self, client, editor, django_assert_num_queries
    ) -> None:
        client.force_login(editor)
        changelist_url = reverse("admin:mvp_compliance_document_changelist")

        for _ in range(2):
            version = VersionFactory()
            version.publish()

        with CaptureQueriesContext(connection) as at_two_documents:
            response = client.get(changelist_url)
        assert response.status_code == 200

        for _ in range(8):
            version = VersionFactory()
            version.publish()

        with django_assert_num_queries(len(at_two_documents.captured_queries)):
            response = client.get(changelist_url)
        assert response.status_code == 200


class TestUserFacingStrings:
    def test_every_string_is_translatable(self) -> None:
        shipped_strings = (
            python_translatable_strings() | template_translatable_strings()
        )
        assert shipped_strings

        catalog_msgids = {msgid for msgid, _msgstr in catalog_entries() if msgid}
        missing = shipped_strings - catalog_msgids

        assert not missing


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestSummaryInTheAdmin:
    def test_a_drafts_summary_is_saved_from_its_page(
        self, client, editor, draft
    ) -> None:
        client.force_login(editor)
        change_url = reverse("admin:mvp_compliance_version_change", args=[draft.pk])

        response = client.post(
            change_url,
            data={
                "document": draft.document_id,
                "markdown": draft.markdown,
                "summary": "We now say how long we keep your address.",
            },
        )

        draft.refresh_from_db()
        assert response.status_code == 302
        assert draft.summary == "We now say how long we keep your address."

    def test_the_next_version_starts_without_the_summary_in_force(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        current = VersionFactory(document=document, summary="The change in force")
        current.publish()

        response = client.get(
            reverse("admin:mvp_compliance_version_add"), {"document": document.pk}
        )

        assert response.status_code == 200
        assert "summary" not in response.context["adminform"].form.initial
        assert current.summary not in response.content.decode()

    def test_a_published_versions_page_shows_its_summary(self, client, editor) -> None:
        version = VersionFactory(summary="We now say how long we keep your address.")
        version.publish()
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[version.pk])
        )

        assert version.summary in response.content.decode()


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestPublisherInTheAdmin:
    def test_publishing_through_the_admin_records_the_signed_in_user(
        self, client, publisher, draft
    ) -> None:
        client.force_login(publisher)

        client.post(reverse("admin:mvp_compliance_version_publish", args=[draft.pk]))

        draft.refresh_from_db()
        assert draft.status == draft.Status.CURRENT
        assert draft.publisher == publisher
        assert draft.publisher_subject == str(publisher.pk)

    def test_a_published_versions_page_shows_who_published_it_beside_when(
        self, client, editor, draft, user
    ) -> None:
        draft.publish(publisher=user)
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk])
        )

        assert str(user) in response.content.decode()

    def test_a_removed_publisher_reads_as_removed_on_the_versions_page(
        self, client, editor, draft, user
    ) -> None:
        draft.publish(publisher=user)
        user.delete()
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk])
        )

        removed = Version.objects.get(pk=draft.pk).publisher_display
        assert removed in response.content.decode()

    def test_the_version_list_shows_the_publisher(
        self, client, editor, draft, user
    ) -> None:
        draft.publish(publisher=user)
        client.force_login(editor)

        response = client.get(reverse("admin:mvp_compliance_version_changelist"))

        assert str(user) in response.content.decode()

    def test_the_documents_list_shows_the_publisher_of_the_version_in_force(
        self, client, editor, draft, user
    ) -> None:
        draft.publish(publisher=user)
        client.force_login(editor)

        response = client.get(reverse("admin:mvp_compliance_document_changelist"))

        assert str(user) in response.content.decode()

    @pytest.mark.parametrize("model", ["version", "document"])
    def test_the_lists_cost_a_fixed_number_of_queries_with_publishers(
        self, client, editor, model, django_assert_num_queries
    ) -> None:
        client.force_login(editor)
        url = reverse(f"admin:mvp_compliance_{model}_changelist")

        def add_published(count):
            for _ in range(count):
                VersionFactory().publish(publisher=UserFactory())

        add_published(2)
        with CaptureQueriesContext(connection) as at_two:
            assert client.get(url).status_code == 200
        add_published(8)
        with django_assert_num_queries(len(at_two.captured_queries)):
            assert client.get(url).status_code == 200


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestPublishAnnouncement:
    def test_a_raising_receiver_leaves_the_publication_standing_and_reported(
        self,
        client,
        publisher,
        draft,
        connect,
        django_capture_on_commit_callbacks,
        caplog,
    ) -> None:

        def fail(sender, **kwargs):
            raise ValueError("receiver broke")

        connect(fail)
        client.force_login(publisher)
        with (
            caplog.at_level("ERROR", logger="django.dispatch"),
            django_capture_on_commit_callbacks(execute=True),
        ):
            response = client.post(
                reverse("admin:mvp_compliance_version_publish", args=[draft.pk])
            )

        draft.refresh_from_db()
        assert draft.status == draft.Status.CURRENT
        assert response.status_code == 302
        assert response.url == reverse(
            "admin:mvp_compliance_version_change", args=[draft.pk]
        )
        shown = list(messages.get_messages(response.wsgi_request))
        assert [m.level for m in shown] == [messages.SUCCESS]
        assert [r for r in caplog.records if r.name == "django.dispatch"]

    def test_a_successful_publication_shows_a_success_message(
        self, client, publisher, draft
    ) -> None:
        client.force_login(publisher)

        response = client.post(
            reverse("admin:mvp_compliance_version_publish", args=[draft.pk])
        )

        levels = [m.level for m in messages.get_messages(response.wsgi_request)]
        assert levels == [messages.SUCCESS]

    def test_a_refused_publication_shows_no_success_message(
        self, client, publisher, published_version
    ) -> None:
        client.force_login(publisher)

        response = client.post(
            reverse("admin:mvp_compliance_version_publish", args=[published_version.pk])
        )

        levels = [m.level for m in messages.get_messages(response.wsgi_request)]
        assert levels == [messages.ERROR]


def locked(**kwargs):
    """Build a version and lock it for translation."""
    version = VersionFactory(**kwargs)
    version.lock_for_translation()
    return version


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestPendingInTheAdmin:
    """A pending version is read-only, discardable, and not counted as published."""

    @pytest.mark.parametrize("address", DRAFT_PRIVACY_ADDRESSES)
    def test_anonymous_reaches_nothing(self, client, address) -> None:
        pending = locked()

        response = client.get(DRAFT_PRIVACY_ADDRESSES[address](pending))

        assert response.status_code == 302
        assert pending.markdown.encode() not in response.content

    @pytest.mark.parametrize("address", DRAFT_PRIVACY_ADDRESSES)
    def test_staff_without_permissions_reaches_nothing(
        self, client, staff_without_permissions, address
    ) -> None:
        pending = locked()
        client.force_login(staff_without_permissions)

        response = client.get(DRAFT_PRIVACY_ADDRESSES[address](pending))

        assert response.status_code == 403
        assert pending.markdown.encode() not in response.content

    def test_a_pending_version_is_shown_read_only(self, client, editor) -> None:
        pending = locked()
        client.force_login(editor)
        change_url = reverse("admin:mvp_compliance_version_change", args=[pending.pk])

        get_response = client.get(change_url)
        post_response = client.post(
            change_url,
            data={"document": pending.document_id, "markdown": "Changed wording"},
        )

        pending.refresh_from_db()
        assert get_response.status_code == 200
        assert b'name="markdown"' not in get_response.content
        assert post_response.status_code == 403
        assert pending.markdown != "Changed wording"
        assert pending.status == Version.Status.PENDING

    def test_a_pending_version_has_no_change_permission_and_a_draft_does(
        self, rf, editor, draft
    ) -> None:
        model_admin = admin.site._registry[Version]
        request = rf.get("/")
        request.user = editor
        pending = locked()

        assert model_admin.has_change_permission(request, pending) is False
        assert model_admin.has_change_permission(request, draft) is True

    def test_a_pending_version_can_be_discarded(self, client, editor, document) -> None:
        client.force_login(editor)
        keeper = VersionFactory(document=document)
        keeper.publish()
        victim = locked(document=document, markdown="Pending wording")
        delete_url = reverse("admin:mvp_compliance_version_delete", args=[victim.pk])

        response = client.post(delete_url, data={"post": "yes"})

        assert response.status_code == 302
        assert not Version.objects.filter(pk=victim.pk).exists()
        keeper.refresh_from_db()
        assert keeper.status == Version.Status.CURRENT

    def test_a_pending_version_is_published_by_the_same_action_as_a_draft(
        self, client, publisher
    ) -> None:
        pending = locked()
        client.force_login(publisher)
        change_url = reverse("admin:mvp_compliance_version_change", args=[pending.pk])
        publish_url = reverse("admin:mvp_compliance_version_publish", args=[pending.pk])

        offered = client.get(change_url).content
        response = client.post(publish_url)

        pending.refresh_from_db()
        assert publish_url.encode() in offered
        assert response.status_code == 302
        assert pending.status == Version.Status.CURRENT

    def test_a_pending_version_alone_reads_as_nothing_in_force(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        locked(document=document, markdown="Pending wording")

        response = client.get(reverse("admin:mvp_compliance_document_changelist"))

        content = response.content.decode()
        assert not VERSION_CHANGE_URL_RE.search(content)
        assert 'field-published_version_count">0<' in content

    def test_a_pending_version_beside_a_version_in_force_is_not_counted(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        VersionFactory(document=document, markdown="Current wording").publish()
        locked(document=document, markdown="Pending rewording")

        response = client.get(reverse("admin:mvp_compliance_document_changelist"))

        assert 'field-published_version_count">1<' in response.content.decode()

    def test_a_document_with_only_a_pending_version_keeps_an_editable_slug(
        self, client, editor, document
    ) -> None:
        client.force_login(editor)
        locked(document=document)

        response = client.get(
            reverse("admin:mvp_compliance_document_change", args=[document.pk])
        )

        assert b'name="slug"' in response.content


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestLockingForTranslation:
    def test_a_drafts_page_offers_locking_to_a_publisher_only(
        self, client, publisher, editor, draft
    ) -> None:
        lock_url = reverse("admin:mvp_compliance_version_lock", args=[draft.pk])
        change_url = reverse("admin:mvp_compliance_version_change", args=[draft.pk])

        client.force_login(publisher)
        offered = client.get(change_url)
        client.force_login(editor)
        withheld = client.get(change_url)

        assert f'href="{lock_url}"'.encode() in offered.content
        assert f'href="{lock_url}"'.encode() not in withheld.content

    def test_a_caller_without_publish_version_is_refused_the_lock_view(
        self, client, editor, draft
    ) -> None:
        client.force_login(editor)
        lock_url = reverse("admin:mvp_compliance_version_lock", args=[draft.pk])

        get_response = client.get(lock_url)
        post_response = client.post(lock_url)

        draft.refresh_from_db()
        assert get_response.status_code == 403
        assert post_response.status_code == 403
        assert draft.status == draft.Status.DRAFT

    def test_a_get_confirms_and_a_post_locks(self, client, publisher, draft) -> None:
        client.force_login(publisher)
        lock_url = reverse("admin:mvp_compliance_version_lock", args=[draft.pk])

        confirmation = client.get(lock_url)
        draft.refresh_from_db()
        assert confirmation.status_code == 200
        assert draft.status == draft.Status.DRAFT

        response = client.post(lock_url)

        draft.refresh_from_db()
        assert response.status_code == 302
        assert draft.status == draft.Status.PENDING

    def test_a_refused_lock_reaches_the_caller_as_a_message(
        self, client, publisher, document
    ) -> None:
        client.force_login(publisher)
        empty = VersionFactory(document=document, markdown="   \n\n   ")

        response = client.post(
            reverse("admin:mvp_compliance_version_lock", args=[empty.pk]), follow=True
        )

        empty.refresh_from_db()
        assert [m.level for m in response.context["messages"]] == [messages.ERROR]
        assert empty.status == empty.Status.DRAFT

    def test_a_pending_versions_page_has_no_form_and_offers_three_controls(
        self, client, publisher
    ) -> None:
        client.force_login(publisher)
        pending = locked()

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[pending.pk])
        )

        content = response.content
        assert response.status_code == 200
        assert b"<textarea" not in content
        assert b'name="_save"' not in content
        for name in ("publish", "return_to_draft"):
            url = reverse(f"admin:mvp_compliance_version_{name}", args=[pending.pk])
            assert f'href="{url}"'.encode() in content
        delete_url = reverse("admin:mvp_compliance_version_delete", args=[pending.pk])
        assert f'href="{delete_url}"'.encode() in content

    def test_a_pending_versions_page_offers_no_locking(self, client, publisher) -> None:
        client.force_login(publisher)
        pending = locked()
        lock_url = reverse("admin:mvp_compliance_version_lock", args=[pending.pk])

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[pending.pk])
        )

        assert f'href="{lock_url}"'.encode() not in response.content

    def test_a_pending_version_returns_to_draft_and_publishes(
        self, client, publisher
    ) -> None:
        client.force_login(publisher)
        returning = locked()
        publishing = locked()

        returned = client.post(
            reverse("admin:mvp_compliance_version_return_to_draft", args=[returning.pk])
        )
        published = client.post(
            reverse("admin:mvp_compliance_version_publish", args=[publishing.pk])
        )

        returning.refresh_from_db()
        publishing.refresh_from_db()
        assert returned.status_code == 302
        assert returning.status == returning.Status.DRAFT
        assert published.status_code == 302
        assert publishing.status == publishing.Status.CURRENT

    def test_a_caller_without_publish_version_is_refused_the_return_view(
        self, client, editor
    ) -> None:
        client.force_login(editor)
        pending = locked()
        return_url = reverse(
            "admin:mvp_compliance_version_return_to_draft", args=[pending.pk]
        )

        get_response = client.get(return_url)
        post_response = client.post(return_url)

        pending.refresh_from_db()
        assert get_response.status_code == 403
        assert post_response.status_code == 403
        assert pending.status == pending.Status.PENDING

    def test_a_get_of_the_return_view_confirms_and_changes_nothing(
        self, client, publisher
    ) -> None:
        client.force_login(publisher)
        pending = locked()

        response = client.get(
            reverse("admin:mvp_compliance_version_return_to_draft", args=[pending.pk])
        )

        pending.refresh_from_db()
        assert response.status_code == 200
        assert pending.status == pending.Status.PENDING

    @pytest.mark.usefixtures("site_languages")
    def test_deleting_permission_alone_discards_a_pending_version_and_its_translations(
        self, client, editor
    ) -> None:
        client.force_login(editor)
        pending = locked()
        TranslationFactory(version=pending, language="de")
        live = TranslationFactory(version=pending, language="fr")
        live.publish()
        delete_url = reverse("admin:mvp_compliance_version_delete", args=[pending.pk])

        confirmation = client.get(delete_url)
        response = client.post(delete_url, data={"post": "yes"})

        assert confirmation.status_code == 200
        assert response.status_code == 302
        assert not Version.objects.filter(pk=pending.pk).exists()
        assert not Translation.objects.filter(version_id=pending.pk).exists()


TRANSLATOR_PERMISSIONS = (
    "add_translation",
    "change_translation",
    "view_translation",
    "view_version",
)


@pytest.fixture
def translator(db):
    """Somebody who may write translations but not put them live."""
    return grant(UserFactory(is_staff=True), *TRANSLATOR_PERMISSIONS)


@pytest.fixture
def translation_publisher(db):
    """Somebody who may write translations and put them live, and nothing on versions."""
    return grant(
        UserFactory(is_staff=True), *TRANSLATOR_PERMISSIONS, "publish_translation"
    )


def add_translation_url(version, language="de") -> str:
    """The address that opens the add form for a version and a language."""
    return (
        reverse("admin:mvp_compliance_translation_add")
        + f"?version={version.pk}&language={language}"
    )


@pytest.mark.django_db
@pytest.mark.urls(__name__)
@pytest.mark.usefixtures("site_languages")
class TestTranslationAdmin:
    @pytest.mark.parametrize("state", ["pending", "published"])
    def test_a_translation_is_added_from_a_pending_or_published_version(
        self, client, translator, state
    ) -> None:
        client.force_login(translator)
        version = locked()
        if state == "published":
            version.publish()

        get_response = client.get(add_translation_url(version))
        post_response = client.post(
            add_translation_url(version),
            data={
                "version": version.pk,
                "language": "de",
                "markdown": "Neuer Wortlaut",
            },
        )

        written = Translation.objects.get(version=version)
        assert get_response.status_code == 200
        assert post_response.status_code == 302
        assert written.language == "de"
        assert written.status == Translation.Status.DRAFT

    @pytest.mark.parametrize(
        "address",
        [
            lambda draft, pending: reverse("admin:mvp_compliance_translation_add"),
            lambda draft, pending: add_translation_url(draft),
            lambda draft, pending: add_translation_url(pending, "en"),
            lambda draft, pending: add_translation_url(pending, "xx"),
            lambda draft, pending: add_translation_url(pending, ""),
            lambda draft, pending: (
                reverse("admin:mvp_compliance_translation_add")
                + "?version=not-a-number&language=de"
            ),
        ],
        ids=[
            "bare",
            "draft version",
            "main language",
            "language not offered",
            "no language",
            "version not a number",
        ],
    )
    def test_the_add_form_is_refused_unless_both_halves_are_valid(
        self, client, translator, draft, address
    ) -> None:
        client.force_login(translator)
        pending = locked()

        response = client.get(address(draft, pending))

        assert response.status_code == 403
        assert not Translation.objects.exists()

    def test_adding_where_one_exists_starts_from_its_current_wording(
        self, client, translator
    ) -> None:
        client.force_login(translator)
        pending = locked()
        existing = TranslationFactory(version=pending, markdown="Bestehender Text")
        existing.publish()

        response = client.get(add_translation_url(pending))

        initial = response.context["adminform"].form.initial
        assert initial["markdown"] == "Bestehender Text"

    def test_adding_a_correction_keeps_the_wording_it_replaces(
        self, client, translation_publisher
    ) -> None:
        client.force_login(translation_publisher)
        pending = locked()
        original = TranslationFactory(version=pending, markdown="Erster Text")
        original.publish()
        client.post(
            add_translation_url(pending),
            data={"version": pending.pk, "language": "de", "markdown": "Besserer Text"},
        )
        correction = Translation.objects.get(
            version=pending, status=Translation.Status.DRAFT
        )

        client.post(
            reverse("admin:mvp_compliance_translation_publish", args=[correction.pk])
        )

        original.refresh_from_db()
        correction.refresh_from_db()
        assert original.status == Translation.Status.SUPERSEDED
        assert original.markdown == "Erster Text"
        assert correction.status == Translation.Status.CURRENT

    def test_a_draft_translation_can_be_edited(self, client, translator) -> None:
        client.force_login(translator)
        draft_translation = TranslationFactory(markdown="Vorher")
        change_url = reverse(
            "admin:mvp_compliance_translation_change", args=[draft_translation.pk]
        )

        page = client.get(change_url)
        response = client.post(change_url, data={"markdown": "Nachher"})

        draft_translation.refresh_from_db()
        assert b'name="markdown"' in page.content
        assert response.status_code == 302
        assert draft_translation.markdown == "Nachher"
        assert draft_translation.language == "de"

    def test_a_translation_holder_can_add_preview_and_put_live_and_nothing_on_versions(
        self, client, translation_publisher
    ) -> None:
        client.force_login(translation_publisher)
        pending = locked()
        client.post(
            add_translation_url(pending),
            data={"version": pending.pk, "language": "de", "markdown": "Text"},
        )
        written = Translation.objects.get(version=pending)

        preview = client.get(
            reverse("admin:mvp_compliance_translation_preview", args=[written.pk])
        )
        confirmation = client.get(
            reverse("admin:mvp_compliance_translation_publish", args=[written.pk])
        )
        put_live = client.post(
            reverse("admin:mvp_compliance_translation_publish", args=[written.pk])
        )

        written.refresh_from_db()
        assert preview.status_code == 200
        assert confirmation.status_code == 200
        assert put_live.status_code == 302
        assert written.status == Translation.Status.CURRENT
        assert written.publisher == translation_publisher

    @pytest.mark.parametrize("name", ["lock", "return_to_draft", "publish"])
    def test_a_translation_holder_is_refused_the_versions_status_views(
        self, client, translation_publisher, name
    ) -> None:
        client.force_login(translation_publisher)
        pending = locked()
        draft_version = VersionFactory()
        url = reverse(f"admin:mvp_compliance_version_{name}", args=[pending.pk])
        draft_url = reverse(
            f"admin:mvp_compliance_version_{name}", args=[draft_version.pk]
        )

        responses = [client.get(url), client.post(url), client.post(draft_url)]

        pending.refresh_from_db()
        draft_version.refresh_from_db()
        assert [r.status_code for r in responses] == [403, 403, 403]
        assert pending.status == pending.Status.PENDING
        assert draft_version.status == draft_version.Status.DRAFT

    def test_a_translation_holder_can_neither_change_nor_delete_a_version(
        self, client, translation_publisher, draft
    ) -> None:
        client.force_login(translation_publisher)
        pending = locked()

        changes = [
            client.post(
                reverse("admin:mvp_compliance_version_change", args=[version.pk]),
                data={"document": version.document_id, "markdown": "Rewritten"},
            )
            for version in (draft, pending)
        ]
        deletes = [
            client.post(
                reverse("admin:mvp_compliance_version_delete", args=[version.pk]),
                data={"post": "yes"},
            )
            for version in (draft, pending)
        ]

        assert [r.status_code for r in changes] == [403, 403]
        assert [r.status_code for r in deletes] == [403, 403]
        assert Version.objects.filter(pk__in=[draft.pk, pending.pk]).count() == 2

    def test_without_publish_translation_the_publish_view_is_refused(
        self, client, translator
    ) -> None:
        client.force_login(translator)
        written = TranslationFactory()
        url = reverse("admin:mvp_compliance_translation_publish", args=[written.pk])

        get_response = client.get(url)
        post_response = client.post(url)

        written.refresh_from_db()
        assert get_response.status_code == 403
        assert post_response.status_code == 403
        assert written.status == Translation.Status.DRAFT

    def test_the_publish_view_checks_publish_translation_only(
        self, client, publisher
    ) -> None:
        client.force_login(publisher)
        written = TranslationFactory()
        url = reverse("admin:mvp_compliance_translation_publish", args=[written.pk])

        response = client.post(url)

        written.refresh_from_db()
        assert response.status_code == 403
        assert written.status == Translation.Status.DRAFT

    def test_a_refused_publication_reaches_the_caller_as_a_message(
        self, client, translation_publisher
    ) -> None:
        client.force_login(translation_publisher)
        written = TranslationFactory(markdown="   \n   ")

        response = client.post(
            reverse("admin:mvp_compliance_translation_publish", args=[written.pk]),
            follow=True,
        )

        written.refresh_from_db()
        assert [m.level for m in response.context["messages"]] == [messages.ERROR]
        assert written.status == Translation.Status.DRAFT

    def test_a_non_draft_translations_page_has_no_form_and_no_delete(
        self, client, translation_publisher
    ) -> None:
        user = grant(translation_publisher, "delete_translation")
        client.force_login(user)
        written = TranslationFactory()
        written.publish()
        change_url = reverse(
            "admin:mvp_compliance_translation_change", args=[written.pk]
        )
        delete_url = reverse(
            "admin:mvp_compliance_translation_delete", args=[written.pk]
        )

        page = client.get(change_url)
        changed = client.post(change_url, data={"markdown": "Anders"})
        deleted = client.post(delete_url, data={"post": "yes"})

        written.refresh_from_db()
        assert page.status_code == 200
        assert b"<textarea" not in page.content
        assert b'name="_save"' not in page.content
        assert f'href="{delete_url}"'.encode() not in page.content
        assert changed.status_code == 403
        assert deleted.status_code == 403
        assert Translation.objects.filter(pk=written.pk).exists()
        assert written.markdown != "Anders"

    def test_the_preview_shows_the_rendering_the_publish_will_store(
        self, client, translation_publisher
    ) -> None:
        client.force_login(translation_publisher)
        written = TranslationFactory(
            markdown="# Titel\n\n**fett** <script>x()</script>"
        )
        expected = get_renderer()().render(written.markdown)

        preview = client.get(
            reverse("admin:mvp_compliance_translation_preview", args=[written.pk])
        )
        confirmation = client.get(
            reverse("admin:mvp_compliance_translation_publish", args=[written.pk])
        )
        client.post(
            reverse("admin:mvp_compliance_translation_publish", args=[written.pk])
        )

        written.refresh_from_db()
        assert expected in preview.content.decode()
        assert expected in confirmation.content.decode()
        assert written.html == expected

    def test_a_put_live_translations_pages_show_its_stored_html(
        self, client, translation_publisher
    ) -> None:
        client.force_login(translation_publisher)
        written = TranslationFactory()
        written.publish()
        stored_html = written.html
        addresses = [
            reverse(f"admin:mvp_compliance_translation_{name}", args=[written.pk])
            for name in ("preview", "change")
        ]

        with override_settings(
            MVP_COMPLIANCE_RENDERER="tests.test_models.UppercaseRenderer"
        ):
            responses = [client.get(address) for address in addresses]

        for response in responses:
            content = response.content.decode()
            assert response.status_code == 200
            assert stored_html in content
            assert stored_html.upper() not in content

    def test_the_change_form_of_a_draft_offers_preview_and_publish_by_permission(
        self, client, translator, translation_publisher
    ) -> None:
        written = TranslationFactory()
        preview_url = reverse(
            "admin:mvp_compliance_translation_preview", args=[written.pk]
        )
        publish_url = reverse(
            "admin:mvp_compliance_translation_publish", args=[written.pk]
        )
        change_url = reverse(
            "admin:mvp_compliance_translation_change", args=[written.pk]
        )

        client.force_login(translation_publisher)
        permitted = client.get(change_url)
        client.force_login(translator)
        withheld = client.get(change_url)

        assert f'href="{preview_url}"'.encode() in permitted.content
        assert f'href="{publish_url}"'.encode() in permitted.content
        assert f'href="{preview_url}"'.encode() in withheld.content
        assert f'href="{publish_url}"'.encode() not in withheld.content


def href(url: str) -> bytes:
    """The attribute a link to this address carries, as the page escapes it."""
    return f'href="{escape(url)}"'.encode()


def put_live(version, language):
    """Write and put live a translation of a version, returning it."""
    translation = TranslationFactory(version=version, language=language)
    translation.publish()
    return translation


def listed_row(content: bytes, language: str) -> str:
    """The opening tag of the row a page gives one language."""
    match = re.search(
        rf'<li[^>]*data-translation-language="{language}"[^>]*>', content.decode()
    )
    assert match, f"no row for {language}"
    return match.group(0)


def filter_parameters(response) -> list[str]:
    """The query parameters the changelist's filters answer to."""
    return [
        getattr(spec, "parameter_name", None)
        for spec in response.context["cl"].filter_specs
    ]


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestVersionTranslations:
    @pytest.mark.usefixtures("site_languages")
    @pytest.mark.parametrize("state", ["pending", "published"])
    def test_the_page_lists_each_offered_language_with_a_way_to_add_or_correct(
        self, client, editor, state
    ) -> None:
        client.force_login(editor)
        version = locked()
        german = put_live(version, "de")
        if state == "published":
            version.publish()

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[version.pk])
        )

        content = response.content
        change_url = reverse(
            "admin:mvp_compliance_translation_change", args=[german.pk]
        )
        assert [
            code
            for code in ("de", "fr")
            if f'data-translation-language="{code}"'.encode() in content
        ] == ["de", "fr"]
        assert href(change_url) in content
        assert href(add_translation_url(version, "de")) in content
        assert href(add_translation_url(version, "fr")) in content
        assert content.count(b'data-translation-language="en"') == 0

    @pytest.mark.usefixtures("site_languages")
    def test_a_language_with_only_a_draft_links_to_the_draft_and_offers_no_second(
        self, client, editor
    ) -> None:
        client.force_login(editor)
        version = locked()
        written = TranslationFactory(version=version, language="fr")

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[version.pk])
        )

        change_url = reverse(
            "admin:mvp_compliance_translation_change", args=[written.pk]
        )
        assert href(change_url) in response.content
        assert href(add_translation_url(version, "fr")) not in response.content

    @pytest.mark.usefixtures("site_languages")
    def test_a_drafts_page_lists_no_translations(self, client, editor, draft) -> None:
        client.force_login(editor)

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[draft.pk])
        )

        assert b"data-translation-language" not in response.content

    def test_with_no_language_offered_and_no_translation_neither_list_nor_filter_appears(
        self, client, editor
    ) -> None:
        client.force_login(editor)
        version = locked()

        page = client.get(
            reverse("admin:mvp_compliance_version_change", args=[version.pk])
        )
        changelist = client.get(reverse("admin:mvp_compliance_version_changelist"))

        assert b"data-translation-language" not in page.content
        assert "missing_translation" not in filter_parameters(changelist)

    @pytest.mark.usefixtures("site_languages")
    def test_the_changelist_offers_the_filter_when_a_language_is_offered(
        self, client, editor
    ) -> None:
        client.force_login(editor)

        response = client.get(reverse("admin:mvp_compliance_version_changelist"))

        assert "missing_translation" in filter_parameters(response)

    @pytest.mark.usefixtures("site_languages")
    @pytest.mark.parametrize(
        ("choice", "expected"),
        [
            ("de", {"french_only", "neither", "published_neither"}),
            ("fr", {"german_only", "neither", "published_neither"}),
            ("any", {"german_only", "french_only", "neither", "published_neither"}),
        ],
    )
    def test_the_filter_narrows_to_versions_missing_a_translation(
        self, client, editor, choice, expected
    ) -> None:
        client.force_login(editor)
        both = locked()
        put_live(both, "de")
        put_live(both, "fr")
        german_only = locked()
        put_live(german_only, "de")
        french_only = locked()
        put_live(french_only, "fr")
        neither = locked()
        published_neither = VersionFactory()
        published_neither.publish()
        VersionFactory()  # a draft, which cannot be translated
        names = {
            german_only.pk: "german_only",
            neither.pk: "neither",
            published_neither.pk: "published_neither",
            both.pk: "both",
            french_only.pk: "french_only",
        }

        response = client.get(
            reverse("admin:mvp_compliance_version_changelist"),
            {"missing_translation": choice},
        )

        listed = {names[v.pk] for v in response.context["cl"].result_list}
        assert listed == expected

    @pytest.mark.usefixtures("site_languages")
    def test_a_kept_translation_is_listed_and_flagged_when_its_language_is_no_longer_offered(
        self, client, editor
    ) -> None:
        client.force_login(editor)
        version = locked()
        german = put_live(version, "de")

        with override_settings(LANGUAGES=[("en", "English")]):
            response = client.get(
                reverse("admin:mvp_compliance_version_change", args=[version.pk])
            )

        row = listed_row(response.content, "de")
        change_url = reverse(
            "admin:mvp_compliance_translation_change", args=[german.pk]
        )
        assert "data-translation-kept" in row
        assert href(change_url) in response.content
        assert href(add_translation_url(version, "de")) not in response.content

    @pytest.mark.usefixtures("site_languages")
    def test_a_kept_translation_is_flagged_when_its_language_became_the_main_one(
        self, client, editor
    ) -> None:
        client.force_login(editor)
        version = locked()
        put_live(version, "de")

        with override_settings(LANGUAGE_CODE="de"):
            response = client.get(
                reverse("admin:mvp_compliance_version_change", args=[version.pk])
            )

        assert "data-translation-kept" in listed_row(response.content, "de")
        assert "data-translation-kept" not in listed_row(response.content, "en")

    @pytest.mark.usefixtures("site_languages")
    def test_an_offered_language_is_not_flagged_as_kept(self, client, editor) -> None:
        client.force_login(editor)
        version = locked()
        put_live(version, "de")

        response = client.get(
            reverse("admin:mvp_compliance_version_change", args=[version.pk])
        )

        assert "data-translation-kept" not in listed_row(response.content, "de")
        assert "data-translation-kept" not in listed_row(response.content, "fr")


@pytest.mark.django_db
@pytest.mark.urls(__name__)
@pytest.mark.usefixtures("site_languages")
class TestTranslationChangelistCost:
    """The translations list costs the same however many rows it shows."""

    def test_the_list_costs_a_fixed_number_of_queries_with_put_live_wordings(
        self, client, translator, django_assert_num_queries
    ) -> None:
        client.force_login(translator)
        url = reverse("admin:mvp_compliance_translation_changelist")

        def add_put_live(count):
            for _ in range(count):
                version = VersionFactory()
                version.publish()
                put_live(version, "de")

        add_put_live(1)
        with CaptureQueriesContext(connection) as at_one:
            assert client.get(url).status_code == 200
        add_put_live(4)
        with django_assert_num_queries(len(at_one.captured_queries)):
            assert client.get(url).status_code == 200
