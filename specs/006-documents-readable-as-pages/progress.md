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

## 2026-09-26T16:10Z · Implementer US-1 · T001–T004

- **Did:** T001 tests for `Document.slug` and `in_force()` (`TestDocumentSlug`, `TestDocumentInForce`), `DocumentFactory` slug sequence, slugs added to the inline creations in `TestDocument`. T002 `Document.slug` (unique `SlugField`, no validator or freeze), `DocumentQuerySet.in_force()` with manager forwarder, migration `0007_document_slug` (default `""` with `preserve_default=False`, so the existing migration round-trip test that holds one document still runs forward), `seed_demo` slugs, `en` catalog regenerated from the repo root. T003 `TestDocumentView` (six tests) and `FLEX_MENUS` in the test settings, `tests/urls.py` mounts `legal/`. T004 `mvp_compliance/urls.py`, `views.py` (`DocumentView`), `document_detail.html`.
- **Verified:** T001 and T003 observed red before the code (`TypeError ... unexpected keyword 'slug'`; `No module named 'mvp_compliance.urls'`). After T004: `uv run pytest tests -q -n auto` all green; `makemigrations --check` clean.
- **Next:** T005 edge-case tests, T006 demo, T007 docs.
- **Watch:** `TestDocument::test_document_holds_no_wording` asserted the field set `{"id", "name"}`; it now lists `slug` (see concerns in the report).

## 2026-09-26T16:20Z · Implementer US-1 · T005

- **Did:** edge-case tests in `TestDocumentView`: draft-only and unknown slug are 404 for anonymous, signed-in and staff; markup in a name is escaped; query count identical for one and five published versions; no edit or delete link drawn for a superuser.
- **Verified:** `uv run pytest tests/test_views.py` 11 passed. Probe: swapping `in_force()` for `all()` in the view turned 10 of 11 red; reverted.
- **Next:** T006 demo wiring.
- **Watch:** `tests/test_app.py` still asserts `mvp_compliance.urls` does not exist; see the report's concerns.

## 2026-09-26T16:25Z · Implementer US-1 · T006

- **Did:** demo `FLEX_MENUS` renderers and `MVP_CONFIG` sidebar title, `legal/` mounted, landing page links the pages of the two documents that have a version in force.
- **Verified:** rebuilt `demo.sqlite3` (`migrate`, `seed_demo`), `manage.py check` clean; on the running server `/legal/privacy-policy/` 200, `/legal/cookie-policy/` (draft only) 404, landing carries the link.
- **Next:** T007 docs, then the full verify.
- **Watch:** none.

## 2026-09-26T16:35Z · Implementer US-1 · T007

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

## 2026-09-26T16:45Z · Implementer US-2 · T008

- **Did:** `TestWithReplacedAt` in `tests/test_models.py`: three versions of one document and one of another, current is `None`, a draft is not a replacement, one query for all.
- **Verified:** `uv run pytest tests/test_models.py::TestWithReplacedAt` 3 failed, all `AttributeError: no attribute 'with_replaced_at'`.
- **Next:** T009 the queryset method.
- **Watch:** none.

## 2026-09-26T16:50Z · Implementer US-2 · T009

- **Did:** `VersionQuerySet.with_replaced_at()`: `Subquery` on the earliest published version of the same document with a later `published_at`.
- **Verified:** `uv run pytest tests/test_models.py::TestWithReplacedAt` 3 passed; ruff clean.
- **Next:** T010 converter test.
- **Watch:** not forwarded on `VersionManager`; the views go through `published()`, which returns a queryset.

## 2026-09-26T16:55Z · Implementer US-2 · T010

- **Did:** `tests/test_urls.py::TestVersionNumberConverter`: `2026.1` and `2026.12` resolve and reverse to `version`; `versions`, `2026`, `26.1`, `2026.x` raise `Resolver404`.
- **Verified:** `uv run pytest tests/test_urls.py` 4 failed (NoReverseMatch / Resolver404 on the missing pattern), 4 passed (the negatives, trivially until T012 adds the pattern).
- **Next:** T011 view tests.
- **Watch:** the negative cases only bite once the pattern exists; re-run after T012.

## 2026-09-26T17:00Z · Implementer US-2 · T011

- **Did:** `TestVersionView` in `tests/test_views.py` (12 tests): superseded and current wording, unchanged after a later publication, another document's number, unpublished number, draft, shell, breadcrumbs, no Markdown rendering, escaped name, constant query count.
- **Verified:** `uv run pytest tests/test_views.py::TestVersionView` 12 failed, all `NoReverseMatch: 'version'`.
- **Next:** T012 converter, pattern, view, template.
- **Watch:** the draft test asserts a draft has no number and that the next number is 404.

## 2026-09-26T17:15Z · Implementer US-2 · T012

- **Did:** `VersionNumberConverter` (registered as `version_number`) and the `version` pattern; `VersionView` overriding `get_object()`, title, subtitle, breadcrumbs; `version_detail.html` (c-alert with dates and a link for a superseded version, "This is the version in force." otherwise).
- **Verified:** `uv run pytest tests/test_views.py tests/test_urls.py tests/test_models.py::TestWithReplacedAt` 34 passed; ruff and mypy clean. Probe: dropping the `document__slug` filter turned the cross-document and query-count tests red; restored. Also fixed my own T011 cross-document test, whose fixture published identical wording (refused by publish).
- **Next:** T013 docs and catalog.
- **Watch:** the query-count test relies on the number-only probe as well.

## 2026-09-26T17:30Z · Implementer US-2 · T013

- **Did:** `docs/pages.md` (the `version` name and arguments, the number's shape, a version's own page in force and replaced, when it is 404, its template); `docs/models.md` (`with_replaced_at()`); `en` catalog regenerated from the repository root with the four new entries filled and the three fuzzy guesses cleared.
- **Verified:** see the full verify below in the report.
- **Next:** full verify, report.
- **Watch:** CHANGELOG `[Unreleased]` has no entry for the version pages; left alone as outside this story's listed files.

## 2026-09-26 — US-2 accepted

Receipts green, independent verify green, tamper-check clean. One wording change by the
orchestrator: the replaced notice named the replacement date twice and now names it once. The
CHANGELOG entry for the version pages is carried into US-3's T018.

## 2026-09-26T17:45Z · Implementer US-3 · T014

- **Did:** `TestVersionListView` (7 tests) and one `TestDocumentView` test for the "Earlier versions" link.
- **Verified:** `uv run pytest tests/test_views.py -k "VersionList or links_to_the_versions"` 8 failed, all `NoReverseMatch: 'versions'`.
- **Next:** T015 pattern, view, template, link.
- **Watch:** the "In force" marker test counts the string in the whole page.

## 2026-09-26T18:00Z · Implementer US-3 · T015

- **Did:** `versions` pattern, `VersionListView`, `version_list.html` (table: number linking to its page, in-force date, replaced date or "In force"), the "Earlier versions" link in `document_detail.html`. Fixed my own marker test (the column header also contains "In force").
- **Verified:** `uv run pytest tests/test_views.py` 31 passed; `ruff check` and `mypy mvp_compliance` clean.
- **Next:** T016 index tests.
- **Watch:** `tests/test_urls.py::TestVersionNumberConverter::test_anything_else_does_not_resolve_to_the_version_address[versions]` (US-2's) now fails by design: `versions` is a real address. Not mine to edit; reported in concerns.

## 2026-09-26T18:10Z · Implementer US-3 · T016

- **Did:** `TestDocumentIndexView` (6 tests): alphabetical and linked, draft-only and empty absent, the "nothing published yet" sentence, shell and title, escaped name, constant query count (2 vs 6 documents).
- **Verified:** `uv run pytest tests/test_views.py -k Index` 6 failed, all `NoReverseMatch: 'index'`.
- **Next:** T017 pattern, view, template, index crumb, demo menu.
- **Watch:** T017 also updates the two US-1/US-2 breadcrumb tests the brief authorises.

## 2026-09-26T18:25Z · Implementer US-3 · T017

- **Did:** `index` pattern (first), `DocumentIndexView` (`MVPTemplateView`, lazy title), `document_index.html`; `index_crumb()` leads the trails of the document, version and version-list views. Updated the two US-1/US-2 breadcrumb assertions to lead with the index (authorised); new `TestBreadcrumbTrails`. `demo/menus.py` adds a "Legal documents" `AppMenu` item; `AppMenu` resolves it at import.
- **Verified:** `uv run pytest tests/test_views.py tests/test_urls.py` 46 passed, 1 failed (the `versions` case in test_urls, see T015); ruff and mypy clean; demo `/legal/` on 8021 answers with the entry.
- **Next:** T018 docs, changelog, catalog.
- **Watch:** ruff removed an unused import it flagged in my first edit.

## 2026-09-26T18:40Z · Implementer US-3 · T018

- **Did:** `docs/pages.md` (index, versions and index URL names, the footer "Legal" link, the demo menu entry, the version list, the two new templates and their context); CHANGELOG `Added` now covers the version pages, the version list and the index; `en` catalog regenerated from the repository root, POT-Creation-Date line deleted, eight fuzzy guesses cleared and filled, no `.mo` committed.
- **Verified:** `uv run pytest -n auto --dist loadscope` 357 passed, 1 failed (the US-2 `versions` case, see T015).
- **Next:** full verify, report.
- **Watch:** the failing test asserts `versions` does not resolve under a slug; it now resolves to the version list on purpose.
