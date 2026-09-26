# Progress — 006 Documents and their versions readable as pages of the site

The running log of this feature's implementation run. The ledger (`feature-state.json`) is the
machine record; this is the readable one.

---

## 2026-09-26 — S3 PLAN

Picked off the feature queue as the one feature ready to build in this repo, with no feature
delivered since the specification landed, so there was nothing to re-read it against. Branch
`006-documents-readable-as-pages` cut from `origin/main` at `0679bea`, which carries the
specification merged in #59. Verify green on that commit: lint, typecheck, tests, build.

Plan, research and tasks written. Four stories, run in sequence: US-1, US-2, US-3, US-4. Analysis
maps every functional requirement to at least one task. No critical findings.

## 2026-09-26 — S3R DESIGN REVIEW

One reviewer, three lenses, receipts green. Verdict: request changes, one verified high finding
(adding the required slug breaks the existing inline document tests and the demo seed; no task said
so) and three low ones. All four applied as plan and task edits, recorded in decisions.md D2 and D3.

## 2026-09-26T15:57Z · Implementer US-1 · T001–T004

- **Did:** T001 tests for `Document.slug` and `in_force()` (`TestDocumentSlug`, `TestDocumentInForce`), `DocumentFactory` slug sequence, slugs added to the inline creations in `TestDocument`. T002 `Document.slug` (unique `SlugField`, no validator or freeze), `DocumentQuerySet.in_force()` with manager forwarder, migration `0007_document_slug` (default `""` with `preserve_default=False`, so the existing migration round-trip test that holds one document still runs forward), `seed_demo` slugs, `en` catalog regenerated from the repo root. T003 `TestDocumentView` (six tests) and `FLEX_MENUS` in the test settings, `tests/urls.py` mounts `legal/`. T004 `mvp_compliance/urls.py`, `views.py` (`DocumentView`), `document_detail.html`.
- **Verified:** T001 and T003 observed red before the code (`TypeError ... unexpected keyword 'slug'`; `No module named 'mvp_compliance.urls'`). After T004: `uv run pytest tests -q -n auto` all green; `makemigrations --check` clean.
- **Next:** T005 edge-case tests, T006 demo, T007 docs.
- **Watch:** `TestDocument::test_document_holds_no_wording` asserted the field set `{"id", "name"}`; it now lists `slug` (see concerns in the report).

## 2026-09-26T15:57Z · Implementer US-1 · T005

- **Did:** edge-case tests in `TestDocumentView`: draft-only and unknown slug are 404 for anonymous, signed-in and staff; markup in a name is escaped; query count identical for one and five published versions; no edit or delete link drawn for a superuser.
- **Verified:** `uv run pytest tests/test_views.py` 11 passed. Probe: swapping `in_force()` for `all()` in the view turned 10 of 11 red; reverted.
- **Next:** T006 demo wiring.
- **Watch:** `tests/test_app.py` still asserts `mvp_compliance.urls` does not exist; see the report's concerns.

## 2026-09-26T15:58Z · Implementer US-1 · T006

- **Did:** demo `FLEX_MENUS` renderers and `MVP_CONFIG` sidebar title, `legal/` mounted, landing page links the pages of the two documents that have a version in force.
- **Verified:** rebuilt `demo.sqlite3` (`migrate`, `seed_demo`), `manage.py check` clean; on the running server `/legal/privacy-policy/` 200, `/legal/cookie-policy/` (draft only) 404, landing carries the link.
- **Next:** T007 docs, then the full verify.
- **Watch:** none.

## 2026-09-26T16:00Z · Implementer US-1 · T007

- **Did:** `docs/pages.md` (mounting, the `document` name, footer link, what a visitor sees, the renderer sentence, when it is "not found", overriding the template); `docs/models.md` slug and `in_force()`; README example and documentation list; CHANGELOG Added entries. Catalog regenerated: no string added since T004, so unchanged.
- **Verified:** `uv run pre-commit run --all-files` green; examples in the docs match the demo and tests.
- **Next:** full verify, report.
- **Watch:** none.

## 2026-09-26 — US-1 accepted

Receipts green. Independent verify on the branch: all steps green after two orchestrator fixes —
the two `test_app.py` tests that pinned "no public addresses" replaced (decisions.md D4), and the
document view named in `docs/pages.md` so the documentation check passes. Tamper-check flags only
the authorised edits: `TestDocument` slugs (D2), `test_app.py` (D4) and the planned `tests/urls.py`
mount.

## 2026-09-26T16:02Z · Implementer US-2 · T008

- **Did:** `TestWithReplacedAt` in `tests/test_models.py`: three versions of one document and one of another, current is `None`, a draft is not a replacement, one query for all.
- **Verified:** `uv run pytest tests/test_models.py::TestWithReplacedAt` 3 failed, all `AttributeError: no attribute 'with_replaced_at'`.
- **Next:** T009 the queryset method.
- **Watch:** none.

## 2026-09-26T16:02Z · Implementer US-2 · T009

- **Did:** `VersionQuerySet.with_replaced_at()`: `Subquery` on the earliest published version of the same document with a later `published_at`.
- **Verified:** `uv run pytest tests/test_models.py::TestWithReplacedAt` 3 passed; ruff clean.
- **Next:** T010 converter test.
- **Watch:** not forwarded on `VersionManager`; the views go through `published()`, which returns a queryset.

## 2026-09-26T16:02Z · Implementer US-2 · T010

- **Did:** `tests/test_urls.py::TestVersionNumberConverter`: `2026.1` and `2026.12` resolve and reverse to `version`; `versions`, `2026`, `26.1`, `2026.x` raise `Resolver404`.
- **Verified:** `uv run pytest tests/test_urls.py` 4 failed (NoReverseMatch / Resolver404 on the missing pattern), 4 passed (the negatives, trivially until T012 adds the pattern).
- **Next:** T011 view tests.
- **Watch:** the negative cases only bite once the pattern exists; re-run after T012.

## 2026-09-26T16:02Z · Implementer US-2 · T011

- **Did:** `TestVersionView` in `tests/test_views.py` (12 tests): superseded and current wording, unchanged after a later publication, another document's number, unpublished number, draft, shell, breadcrumbs, no Markdown rendering, escaped name, constant query count.
- **Verified:** `uv run pytest tests/test_views.py::TestVersionView` 12 failed, all `NoReverseMatch: 'version'`.
- **Next:** T012 converter, pattern, view, template.
- **Watch:** the draft test asserts a draft has no number and that the next number is 404.

## 2026-09-26T16:06Z · Implementer US-2 · T012

- **Did:** `VersionNumberConverter` (registered as `version_number`) and the `version` pattern; `VersionView` overriding `get_object()`, title, subtitle, breadcrumbs; `version_detail.html` (c-alert with dates and a link for a superseded version, "This is the version in force." otherwise).
- **Verified:** `uv run pytest tests/test_views.py tests/test_urls.py tests/test_models.py::TestWithReplacedAt` 34 passed; ruff and mypy clean. Probe: dropping the `document__slug` filter turned the cross-document and query-count tests red; restored. Also fixed my own T011 cross-document test, whose fixture published identical wording (refused by publish).
- **Next:** T013 docs and catalog.
- **Watch:** the query-count test relies on the number-only probe as well.

## 2026-09-26T16:04Z · Implementer US-2 · T013

- **Did:** `docs/pages.md` (the `version` name and arguments, the number's shape, a version's own page in force and replaced, when it is 404, its template); `docs/models.md` (`with_replaced_at()`); `en` catalog regenerated from the repository root with the four new entries filled and the three fuzzy guesses cleared.
- **Verified:** see the full verify below in the report.
- **Next:** full verify, report.
- **Watch:** CHANGELOG `[Unreleased]` has no entry for the version pages; left alone as outside this story's listed files.

## 2026-09-26 — US-2 accepted

Receipts green, independent verify green, tamper-check clean. One wording change by the
orchestrator: the replaced notice named the replacement date twice and now names it once. The
CHANGELOG entry for the version pages is carried into US-3's T018.

## 2026-09-26T16:08Z · Implementer US-3 · T014

- **Did:** `TestVersionListView` (7 tests) and one `TestDocumentView` test for the "Earlier versions" link.
- **Verified:** `uv run pytest tests/test_views.py -k "VersionList or links_to_the_versions"` 8 failed, all `NoReverseMatch: 'versions'`.
- **Next:** T015 pattern, view, template, link.
- **Watch:** the "In force" marker test counts the string in the whole page.

## 2026-09-26T16:08Z · Implementer US-3 · T015

- **Did:** `versions` pattern, `VersionListView`, `version_list.html` (table: number linking to its page, in-force date, replaced date or "In force"), the "Earlier versions" link in `document_detail.html`. Fixed my own marker test (the column header also contains "In force").
- **Verified:** `uv run pytest tests/test_views.py` 31 passed; `ruff check` and `mypy mvp_compliance` clean.
- **Next:** T016 index tests.
- **Watch:** `tests/test_urls.py::TestVersionNumberConverter::test_anything_else_does_not_resolve_to_the_version_address[versions]` (US-2's) now fails by design: `versions` is a real address. Not mine to edit; reported in concerns.

## 2026-09-26T16:08Z · Implementer US-3 · T016

- **Did:** `TestDocumentIndexView` (6 tests): alphabetical and linked, draft-only and empty absent, the "nothing published yet" sentence, shell and title, escaped name, constant query count (2 vs 6 documents).
- **Verified:** `uv run pytest tests/test_views.py -k Index` 6 failed, all `NoReverseMatch: 'index'`.
- **Next:** T017 pattern, view, template, index crumb, demo menu.
- **Watch:** T017 also updates the two US-1/US-2 breadcrumb tests the brief authorises.

## 2026-09-26T16:10Z · Implementer US-3 · T017

- **Did:** `index` pattern (first), `DocumentIndexView` (`MVPTemplateView`, lazy title), `document_index.html`; `index_crumb()` leads the trails of the document, version and version-list views. Updated the two US-1/US-2 breadcrumb assertions to lead with the index (authorised); new `TestBreadcrumbTrails`. `demo/menus.py` adds a "Legal documents" `AppMenu` item; `AppMenu` resolves it at import.
- **Verified:** `uv run pytest tests/test_views.py tests/test_urls.py` 46 passed, 1 failed (the `versions` case in test_urls, see T015); ruff and mypy clean; demo `/legal/` on 8021 answers with the entry.
- **Next:** T018 docs, changelog, catalog.
- **Watch:** ruff removed an unused import it flagged in my first edit.

## 2026-09-26T16:10Z · Implementer US-3 · T018

- **Did:** `docs/pages.md` (index, versions and index URL names, the footer "Legal" link, the demo menu entry, the version list, the two new templates and their context); CHANGELOG `Added` now covers the version pages, the version list and the index; `en` catalog regenerated from the repository root, POT-Creation-Date line deleted, eight fuzzy guesses cleared and filled, no `.mo` committed.
- **Verified:** `uv run pytest -n auto --dist loadscope` 357 passed, 1 failed (the US-2 `versions` case, see T015).
- **Next:** full verify, report.
- **Watch:** the failing test asserts `versions` does not resolve under a slug; it now resolves to the version list on purpose.

## 2026-09-26 — US-3 accepted

Receipts green. Two orchestrator fixes before acceptance: US-2's converter test no longer lists
`versions` as unresolvable, and a test now asserts it resolves to the list (decisions.md D5); the
index crumb helper, renamed with a leading underscore to dodge the docs check, is now
`DocumentIndexView.crumb()`. Independent verify green; tamper-check flags only the authorised
breadcrumb assertion.

## 2026-09-26T16:13Z · Implementer US-4 · T019

- **Did:** `TestDocumentSlug` gains the validator cases (capitals, underscore, leading and trailing hyphen refused; valid slug accepted) and the freeze cases (free before publication through `save()` and `update()`; after publication `save()`, `update(slug=...)` and `bulk_update` raise `PublishedVersionError` with the stored slug unchanged; a superseded version also fixes it; an unchanged slug still saves; the name changes and the page keeps its address).
- **Verified:** `uv run pytest tests/test_models.py::TestDocumentSlug -q` failed 8 of 15, each for the right reason (validation error not raised, `PublishedVersionError` not raised).
- **Next:** T020.
- **Watch:** `bulk_update` raises inside `transaction.atomic(savepoint=False)`, so its test supplies a savepoint the way the existing Version test does.

## 2026-09-26T16:16Z · Implementer US-4 · T020

- **Did:** `lowercase_slug` validator on `Document.slug`; `Document.save()` reads the stored slug with one query only when the instance has a pk and refuses a change once any version is published; `DocumentQuerySet.update()` refuses `slug` for a queryset holding a document with a current or superseded version. Migration `0007` regenerated in place with the validator (`default=''`, `preserve_default=False`).
- **Verified:** `uv run pytest tests/test_models.py::TestDocumentSlug tests/test_migrations.py -q` 17 passed; `makemigrations --check` clean; ruff clean.
- **Next:** T021.
- **Watch:** `Document.SLUG_FIXED_MESSAGE` is a public class attribute shared by the two guards; the docs check may ask for it to be documented.

## 2026-09-26T16:16Z · Implementer US-4 · T021

- **Did:** `TestDocumentSlugInTheAdmin` in `tests/test_admin.py`: add form prepopulates the slug from the name; an unpublished document's slug is editable; a published document's slug is not a form field and is shown; a POST with a different slug leaves it unchanged and still saves the name.
- **Verified:** `uv run pytest tests/test_admin.py::TestDocumentSlugInTheAdmin -q` 3 failed, 1 passed (the editable case already held), failing for the right reasons: no prepopulation, and the admin save raised `PublishedVersionError`.
- **Next:** T022.
- **Watch:** none.

## 2026-09-26T16:17Z · Implementer US-4 · T022

- **Did:** `DocumentAdmin.prepopulated_fields`, `get_readonly_fields` (adds `slug` when the document has a published version), `get_prepopulated_fields` (empty in the same case).
- **Verified:** `uv run pytest tests/test_admin.py::TestDocumentSlugInTheAdmin tests/test_admin.py::TestDocumentAdmin tests/test_admin.py::TestDocumentChangelist -q` 20 passed; ruff clean.
- **Next:** T023.
- **Watch:** none.

## 2026-09-26T16:17Z · Implementer US-4 · T023

- **Did:** `TestTemplateOverride` (a test-only `tests/project_templates/` directory placed first in `TEMPLATES["DIRS"]` holds `mvp_compliance/document_detail.html` and `version_list.html`; the document page and the version list render the overrides, the version page still renders the packaged template) and `TestNoMenuEntry` (`AppMenu` children unchanged after serving all four pages; no package module references the menu library) in `tests/test_views.py`.
- **Verified:** `uv run pytest tests/test_views.py::TestTemplateOverride tests/test_views.py::TestNoMenuEntry -q` 5 passed. These pass by design (the behaviour is already on the branch); the override case is the probe that the templates directory takes effect, since the marker ids exist only in the override files.
- **Next:** T024.
- **Watch:** `AppMenu` is empty under `tests/settings.py` (the demo's entry lives in `demo/menus.py`, not loaded), confirmed before asserting.

## 2026-09-26T16:19Z · Implementer US-4 · T024

- **Did:** `docs/pages.md` "Overriding a template" (a table of every template path, its page and context, and how to override with an example); `docs/models.md` (slug format, when it is fixed, the error); `docs/authoring.md` "Choosing the slug"; `CONTEXT.md` **Slug**; CHANGELOG entry; `en` catalog regenerated from the repository root (POT-Creation-Date line removed, one fuzzy entry fixed, no `.mo`); `tests/locale/de` gains "This is the version in force." with the `.mo` recompiled. `TestPageStrings` in `tests/test_views.py`: every msgid of each page template (translate tags and blocktranslate bodies) is in the `en` catalog; the version page renders the sentence in German; no page template msgid and no rendered page text contains "compliant", "compliance" or "GDPR".
- **Verified:** `uv run pytest tests/test_views.py tests/test_admin.py::TestUserFacingStrings -q` 58 passed. Probe: renaming the "Earlier versions" catalog entry made the catalog test fail for `document_detail.html`; restored.
- **Next:** full verify, report.
- **Watch:** `TestPageStrings` imports `catalog_entries` from `tests/test_admin.py` rather than duplicating the parser.

## 2026-09-26 — US-4 accepted, S5 CONVERGE

US-4: receipts green, independent verify green, tamper-check flags only a moved import in
`tests/test_views.py`. Task evidence written to the ledger by the orchestrator (the implementer left
it).

Converge: every functional requirement traced to a delivered task. One migration on the branch
(`0007_document_slug`), nothing to consolidate. Cleanup pass over the feature diff found nothing to
simplify. D1 graduated to ADR 0019. D2 to D5 declined with reasons.

## 2026-09-26 — S6 REVIEW

One reviewer, correctness, conformance to the spec and security, receipts green. Verdict:
approve, no critical, high or medium findings. Two low findings fixed by the orchestrator: a save
whose `update_fields` leaves the slug out is no longer refused, and `docs/models.md` states that
`update()` and `bulk_update()` refuse any slug on a published document. Outcome recorded on the pull
request.

## 2026-09-26T19:30Z · Implementer US1 · T025

- Did: `TestPageSubtitle` in `tests/test_views.py` — anonymous, signed-in without acceptance, signed-in with acceptance (both pages), superseded version, other-version and other-person acceptances, constant query count. Updated the two old subtitle assertions and the "Earlier versions" link assertion (authorised).
- Verified: `uv run pytest tests/test_views.py -k TestPageSubtitle` — 3 failed on the old subtitle text, 6 passed. Unique (subject, version) means one acceptance per person per version, so "earliest" needs no test.
- Next: T026.
- Watch: the link test now publishes two versions, since the versions link lives in the dropdown (T028).

## 2026-09-26T19:40Z · Implementer US1 · T026

- Did: `VersionSubtitleMixin` in `views.py` (public, one `get_page_subtitle`), used by `DocumentView` and `VersionView`; `VersionView.get_version()` returns its object. Acceptance read through `Acceptance.objects.for_person(user).filter(version=...)`, one query, only for signed-in visitors. The two pre-existing document-page tests that asserted "Version N" now assert the new line.
- Verified: `uv run pytest tests/test_views.py` — all pass except `test_the_page_links_to_the_versions_of_the_document`, which waits on T028. ruff and mypy clean.
- Next: T027.
- Watch: the mixin must be quoted in `docs/pages.md` (T028). The old msgid "Version %(number)s, in force since %(date)s" is gone; catalog regeneration is T028.

## 2026-09-26T19:50Z · Implementer US1 · T027

- Did: `TestPreviousVersionsMenu` in `tests/test_views.py` — earlier published versions newest first with their links and lines, ending in "All versions", no draft, no menu with one published version, no "Earlier versions" text link, constant query count.
- Verified: `uv run pytest tests/test_views.py -k TestPreviousVersionsMenu` — 5 failed for the missing dropdown and the old link still present, 1 passed (the count guard).
- Next: T028.
- Watch: the tests locate the menu from the first `data-mvp-dropdown`; if the shell draws another one earlier, narrow the helper.

## 2026-09-26T20:05Z · Implementer US1 · T028

- Did: `previous_versions` in `DocumentView` context (one query, published versions other than the current, newest first); `document_detail.html` fills `page.actions` with `<c-dropdown>` and drops the text link; `docs/pages.md` describes the line under the name, `VersionSubtitleMixin`, the dropdown and the new context key; en catalog regenerated (POT-Creation-Date removed, three fuzzy entries and one empty msgstr filled, no `.mo`). The end-of-file hook added the missing final newline to `review-brief.json`; committed with this task.
- Verified: `uv run pytest tests/test_views.py` — 70 passed.
- Next: full verify, report.
- Watch: the catalog carries line-number churn in unrelated location comments, which `makemessages` produces.

## 2026-09-26 — Walkthrough changes accepted

T025–T028 verified independently: receipts green, full verify green, tamper-check flags only the
subtitle and "Earlier versions" assertions the brief authorised. Checked on the demo data: the
version line with and without "Agreed on", and the "Previous versions" menu present with earlier
versions and absent without them.
