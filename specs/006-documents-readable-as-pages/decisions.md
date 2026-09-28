# Decisions — 006 Documents and their versions readable as pages of the site

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — A document's address comes from a slug, not its name

**Ambiguous**: the issue asks for an address that keeps working, and a document today has only a
name. The name is the obvious thing to build an address from.

**Chosen**: each document gains a slug, suggested from its name, editable until the document's first
version is published and fixed from then on (FR-015 to FR-017). The name stays editable for ever.

**Why defensible**: names get reworded. "Terms" becomes "Terms of use", and a privacy policy gets
renamed when a site adds a second one for a different audience. An address built from the name
would break every footer link and every link already sent to somebody at exactly that moment, which
is the failure the issue exists to prevent. Freezing at first publication rather than at creation
lets a typo be fixed while it costs nothing, because no address is served until something is
published. This follows the same rule as the rest of the package: what has been published is not
changed.

**ADR:** docs/adr/0019-a-documents-address-is-fixed-once-a-version-is-published.md

## D2 — The existing document tests gain a slug

**Ambiguous**: adding a unique, required slug means every test that creates a document inline
without one now fails on the second document, because an unset slug is the empty string and two
empty strings collide. Changing a test this feature did not write is normally refused.

**Chosen**: the inline creations in `tests/test_models.py::TestDocument` each get a distinct slug,
with no assertion changed. `test_duplicate_name_is_refused` gives its second document a different
slug, so that it keeps proving the name constraint rather than passing on the slug one. `test_document_holds_no_wording` lists the document's fields, so its expected set gains `slug`; what it proves, that a document holds no wording, is unchanged.

**Why defensible**: the tests are rewritten only to supply a value the model now requires. What
they assert is unchanged, and the one test whose meaning a shared slug would have silently changed
is adjusted so that it still tests what its name says. Found by the design review (SPEC-001).

**ADR:** none — a local test adjustment, nothing downstream inherits it.

## D3 — Design review outcome

One verified high finding (SPEC-001, D2 above) and three low ones. All four were applied as edits
to `tasks.md` and `plan.md`: T001/T002 fix the existing tests and the demo seed in the same task
that adds the slug, T002 adds the manager forwarder, the views section says what each view must
override, and T024 gains the no-compliance-claim assertion. The note that `pyproject.toml` lists
only Django 5.2 and 6.0 was checked and is wrong: 6.1 is listed.

**ADR:** none — a record of this feature's review, not a durable decision.

## D4 — The package now has public addresses

**Ambiguous**: `tests/test_app.py` held two tests asserting the package ships no `urls` module,
from FS-002 (its D11) and FS-004 (T031). This feature exists to add one.

**Chosen**: the two tests are replaced by one asserting the module exists and is namespaced
`mvp_compliance`, citing the specs it supersedes, the same way FS-002's D11 replaced FS-001's
assertion.

**Why defensible**: a later approved specification supersedes an earlier one where they conflict.
Both old tests pinned a boundary that was true of the features that wrote them, and FS-006 moves it
on purpose.

**ADR:** none — the supersession is recorded here and in the test's docstring.

## D5 — "versions" is the version list, not a malformed number

**Ambiguous**: US-2's converter test listed `versions` among the segments that must not resolve at
all. US-3 adds the version list at exactly that address.

**Chosen**: `versions` leaves that list, and a separate test asserts it resolves to the `versions`
address. The remaining cases still prove that a malformed number resolves to nothing.

**Why defensible**: the US-2 test was checking that `versions` is never taken for a version number.
That is still true, and the new test states it more precisely.

**ADR:** none — local to this feature's tests.

## D6 — The second walkthrough removes the version list and its tests

**Ambiguous**: T029's brief authorised rewriting `tests/test_urls.py::test_versions_is_the_version_list_not_a_number`
into a test that `/legal/<slug>/versions/` is `Resolver404`, and deleting `TestVersionListView` and
every other assertion about the list page or the "All versions" menu item — tests this feature's
own earlier tasks (T014, T027) wrote and that were passing.

**Chosen**: removed `TestVersionListView` in full; removed `test_the_menu_ends_with_a_link_to_the_version_list`,
the "All versions" assertions in `TestDocumentView` and `TestPageStrings`, the versions entry in
`TestBreadcrumbTrails` and `TestTemplateOverride`, and the versions case in `TestNoMenuEntry`'s loop.
`tests/test_urls.py::test_versions_is_the_version_list_not_a_number` became
`test_versions_is_still_not_a_number`, asserting `Resolver404` (this reverses D5).

**Why defensible**: the maintainer ruled at the second walkthrough that a separate list page is
overkill now the document page carries a "Previous versions" dropdown (FR-011, spec.md
Clarifications). The deleted tests pinned a page that no longer exists; keeping them would pin dead
code. Every deletion is named in the FS-006/US3 completion report's `deviations`, per the brief.

**ADR:** none — recorded here and in the task brief that authorised it.

## D7 — The third walkthrough removes the version page and its tests

**Ambiguous**: T031's brief authorised deleting or rewriting every pre-existing test that exercised
`VersionView`, the `mvp_compliance:version` URL name or `VersionNumberConverter`, and every
assertion about the old "Previous versions" label or behaviour (no menu on a single-version
document, only earlier versions listed) — tests this feature's own earlier tasks (T011, T027, T030)
wrote and that were passing.

**Chosen**: removed `TestVersionView` and `TestPreviousVersionsMenu` in full; rewrote
`subtitle_addresses`/`version_address` in `tests/test_views.py` to build `?version=` addresses
instead of reversing the removed URL name; rewrote every test that reversed
`mvp_compliance:version` directly (`TestPageSubtitle`'s query-count test, `TestTemplateOverride`'s
no-override test, `TestNoMenuEntry`'s menu sweep, `TestPageStrings`'s compliance-wording sweep and
German-rendering test) to use the document address with `?version=` instead; deleted
`tests/test_urls.py` (it tested only the removed converter). The content those old tests
demonstrated — a superseded version's stored HTML, an earlier version's wording surviving a later
publication, 404 for another document's number, a never-published number and a draft's would-be
number — is ported into new `TestDocumentView` methods addressed by `?version=`.

**Why defensible**: the maintainer ruled at the third walkthrough that there is one canonical page
per document, the version chosen by `?version=`, and no separate page or address for a version
(spec.md Clarifications). The deleted and rewritten tests pinned a URL, view and label that no
longer exist; keeping them unrewritten would leave the suite red for reasons unrelated to any real
regression. Every deletion is named in the FS-006/US2 completion report's `deviations`, per the
brief.

**ADR:** none — recorded here and in the task brief that authorised it.

## D8 — One page-strings sanity check drops its per-template assertion

**Ambiguous**: `TestPageStrings.test_every_string_in_a_page_template_is_in_the_english_catalog`
asserted `msgids` non-empty for every page template, as well as `msgids <= catalog`. Between T031
(which removes the old "Previous versions" dropdown, `document_detail.html`'s only translatable
content at the time) and T032 (which adds the replaced-version alert), `document_detail.html`
legitimately carries no translatable string for one commit.

**Chosen**: dropped `assert msgids` from the per-template, per-path test (it still asserts
`msgids <= catalog`, which holds vacuously for an empty set and is the only claim SC-008 actually
makes) and added a separate `test_at_least_one_page_carries_a_translatable_string`, asserting the
same sanity property — that the extraction regex is finding real strings somewhere — across all
page templates together rather than each one individually.

**Why defensible**: the per-template non-empty assertion was never a stated requirement (FR-019,
SC-008); it was an incidental strictness that happened to hold while every existing page carried a
menu or a sentence. Nothing in the spec says every page must always carry translatable text. This
change is not one of T031's authorised removals in the strict sense (it does not exercise the
removed view, URL or converter directly), so it is logged here rather than folded silently into D7.

**ADR:** none — recorded here and in the T031 completion report's `deviations`.
