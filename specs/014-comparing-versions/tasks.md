# Tasks — 014 Comparing two versions of a document

Derived from [plan.md](./plan.md). Task ids are stable. Every task that changes behaviour follows
Article I: the failing test comes first. Tests find elements by fixture data, id, address or
`data-` hook, never by wording.

The approved sketch's templates, copy and stylesheet are kept. Documentation is written in the
story that introduces the public name.

Order: Foundational, US-1, US-2, US-3, then the staff page.

## Foundational

| Id | Task | Done when |
|---|---|---|
| T001 | Remove the sketch's bare-address default from `ComparisonView` (both `from` and `to` required) and the admin's `with_version_links` wrapper with its template branch, keeping the plain version text | Full suite green apart from the catalogue tests the sketch already failed; pre-commit green |

## US-1 — Comparing any two published versions of a document (P1, issue #136)

### Group 1 — the comparison

| Id | Task | Done when |
|---|---|---|
| T002 | `tests/test_comparison.py` — with versions published from Markdown through the factories: added words are inside `ins` and removed inside `del`, and no word the two share is marked (FR-002); one word changed in a long paragraph marks that word alone (FR-003); a heading, a list item and a link that change keep their elements, a removed list item or paragraph is removed whole with its own element (FR-004); the output with the marks taken out holds no tag absent from both inputs, and text that looks like markup stays escaped, including a version row built directly with a raw `>` inside an attribute value and `<img ...>` as text (FR-006); the output run through `html.parser` with a tag stack closes every element in order, for a `ul` that became an `ol`, a list replaced by a paragraph and a paragraph replaced by a list (FR-004); `of()` with either order gives the same older and newer (FR-008); a version with itself, two identical wordings, and two that differ only in a link's address or in a word's wrapping element are `same` and the output marks nothing (FR-010, D16); whitespace-only differences mark nothing; each mark starts with a hidden label | Fails before T003 |
| T003 | `Comparison` as planned, with `similarity` and `window` as class attributes and the quote-aware tag pattern | T002 passes |
| T004 | `tests/test_comparison.py::TestSpeed` — the number of pairing comparisons for two texts of about 1,000 fifteen-word list items that share nothing is at most elements × `window`; two texts of about 15,000 words changed throughout, and two that share nothing, each compare in under one second (SC-004) | Fails before the window is in place, passes with T003 |

### Group 2 — the page and the document's page

| Id | Task | Done when |
|---|---|---|
| T005 | `tests/test_views.py::TestComparisonPage` — anonymous GET with two numbers answers 200, names both versions with links to each version's page (FR-001, FR-007); the reversed order gives the same page (FR-008); the same address gives the same output after a newer version is published (FR-009); a draft's id, a number of another document, an unknown number, a missing `from` or `to`, an unknown slug, a document with only drafts, and any pair on a document with one published version answer 404 for anonymous and staff (FR-011); with the renderer and `markdown.markdown` patched to raise, the page still answers 200 (FR-005); `from` equal to `to` shows the no-differences alert, found by its `data-` hook (FR-010); the page renders in the shell with no project template (FR-020); query count is the same for a document with 2 and with 40 versions (SC-006) | Fails before T006 |
| T006 | `ComparisonView` and the route as planned | T005 passes |
| T007 | `tests/test_views.py::TestDocumentPageComparisons` — a document with several versions offers a comparison link to each other version from the one shown, and one with a single version offers none (FR-012); a superseded version's alert links to its comparison with the version in force (FR-013); the page's query count is what it is on main | Fails before T008 (the sketch adds a query) |
| T008 | `DocumentView`: delete the sketch's `current` query; the template takes the version in force as the first of `versions` | T007 passes |
| T009 | The comparison's strings and the document page's new strings in the English catalogue; `comparison.html` in the page-strings test's list. Documentation for US-1: `docs/pages.md` "Comparing two versions" (what it shows, where it is offered, its address); README's list of pages; `CHANGELOG.md` *Added*; FS-006's spec brought up to date | Catalogue tests green; docs check green |

## US-2 — Seeing what changed since I last agreed (P1, issue #137)

| Id | Task | Done when |
|---|---|---|
| T010 | `tests/test_views.py::TestAgreedDocumentsComparison` — a document whose newest accepted version is not in force links to the comparison from that version to the version in force, and one accepted at the version in force does not (FR-015); with versions 1 and 2 accepted and 4 in force, the link compares 2 with 4; the newest accepted version is read from the acceptances (FR-018); the query count is the same for one document and for five (FR-019) | Fails before T011 |
| T011 | `AgreedDocumentsView.get_entries` sets `since` | T010 passes |
| T012 | `tests/test_views.py::TestAgreementPageComparison` — a document accepted at an earlier version links to its comparison with the version asked about, and one never accepted does not (FR-016); several documents, some agreed before, each linked or not as such, with a query count that does not grow with the documents (FR-019); the link opens in a new tab and the form's destination field is unchanged, and opening the comparison records nothing (FR-017); #132's summaries still render beside it | Fails before T013 |
| T013 | `AgreementView.get_entries` sets `since` in one query; the row component's `since` prop | T012 passes |
| T014 | New strings in the catalogue. Documentation for US-2: `docs/pages.md` in "What a person has agreed to" and "Asking a person to agree"; FS-008 and FS-009 specs brought up to date | Catalogue tests green; docs check green |

## US-3 — Linking to a comparison from the project's own pages (P3, issue #139)

| Id | Task | Done when |
|---|---|---|
| T015 | `tests/test_views.py::TestComparisonTemplate` — `reverse("mvp_compliance:comparison", args=[slug])` with `from` and `to` opens the comparison (FR-021); a project template at `mvp_compliance/comparison.html` is used and is given `comparison`, `versions` and `document` (FR-020). Written to pass: T006 already delivers this, and the test holds it for developers | Passes |
| T016 | Documentation for US-3: `docs/pages.md` how to link to a comparison from a template or an email, and the template under "Overriding a template" with what it is given (FR-024) | Docs check green |

## Alongside the stories — the staff page

| Id | Task | Done when |
|---|---|---|
| T017 | `tests/test_records.py` — each entry carries its version's `version_id`, with no extra query. `tests/test_admin.py` — on the staff page, a reader who may view versions sees each version as a link to its admin change page, and one holding `produce_disclosure` alone sees plain text | Fails before T018 |
| T018 | `AcceptanceEntry.version_id`, its docstring saying the key is there for the staff page's link; the partial's link under `perms.mvp_compliance.view_version`; `docs/disclosure.md`; FS-004's spec brought up to date; `CHANGELOG.md` *Changed* | T017 passes; full suite and pre-commit green |

## Review fixes

| Id | Task | Done when |
|---|---|---|
| T019 | An element over `Comparison.longest` (2,000) words is removed and added whole; a word-less element is compared by its element names and never paired; the limit and the table-cell case documented | A 15,000-word paragraph of repeated words compares in under a second and fails without the cap; a removed list beside a new rule keeps its wrapper |
