# Tasks — 008 What a person has agreed to, in their account area

Derived from [plan.md](./plan.md). Task ids are stable and are what `feature-state.json` tracks.
Every task that changes behaviour follows Article I: the failing test comes first. Tests find
elements by fixture data, role or id, never by wording.

Documentation is not batched into a closing story. Each public name is documented in the story that
introduces it.

## Foundational

| Id | Task | Done when |
|---|---|---|
| T001 | Remove the prototype's untested Python: `AgreedDocumentsView` and its imports from `views.py`, the `agreed/` route from `urls.py`, `mvp_compliance/menus.py`, and the demo landing page's link to the list. Keep the templates, `pages.css` and the seed data. Regenerate the `en` catalog for the document page's new string. `TestPageStrings.test_the_page_template_is_the_document_page` names the three page templates | Full suite green; `makemessages` clean |
| T002 | `docs/pages.md`: the document page's two columns, the pinned list and `--mvp-compliance-header-clearance`. `CHANGELOG.md` `[Unreleased]` *Changed*: the document page's markup | Docs check green on the branch |

## US-1 — Seeing what I agreed to, where I manage my account (P1, issue #78)

| Id | Task | Done when |
|---|---|---|
| T003 | `tests/test_models.py::TestAcceptancesOfAgreedDocuments` — `for_person(user).of_agreed_documents()` returns exactly that user's acceptances of documents people agree to (SC-001); a notice's acceptance, recorded before it became a notice, is left out and returns when the kind is changed back (scenario 8, edge case 2); order is document name, then newest published first (scenario 2, FR-002); a version never accepted between two accepted ones is absent (edge case 1); one query with the version and document loaded | Fails before T004 |
| T004 | `mvp_compliance/models.py` — `AcceptanceQuerySet.of_agreed_documents()` and its manager forwarder per plan.md *The query* | T003 passes |
| T005 | `tests/test_views.py::TestAgreedDocuments` (the test URLconf mounts `mvp.urls`) — one accepted version is listed with its number and acceptance date (scenario 1); three versions of one document appear under one entry, newest published first (scenario 2); each listed version links to `?version=<number>` of its document, current and superseded alike, and following it serves that version's stored HTML (scenarios 3, 4, SC-002); two users each see only their own (scenario 5); a staff user sees only their own; an address with anything appended is not found (FR-004); no acceptances gives 200 with no entries (scenario 6); an anonymous request redirects to sign-in and the response carries no record (scenario 7); a document made a notice is not listed (scenario 8); a document never accepted is not listed (scenario 9); a document's present name is shown after a rename (edge case 3); a name containing markup is escaped; more than four accepted versions gives three in `shown` and the rest in `earlier`, all present in the page, and four gives four and none (scenarios 11, 12, FR-019); the query count is the same with one acceptance as with fifty across ten documents (FR-015, SC-005); opening the page leaves the counts of acceptances, disclosures, versions and documents unchanged (FR-016); `POST` is refused with 405 (FR-010) | Fails before T006 |
| T006 | `mvp_compliance/views.py` — `AgreedDocumentsView` per plan.md *The view*, without `newer` and without the "not found" branch; `urls.py` — the `agreed/` route first | T005 passes; full suite green |
| T007 | `tests/test_menus.py::TestAccountAreaEntry` — for a signed-in request, the processed `AccountCenterMenu` has an entry whose address is the list's (scenario 10, SC-004); on the list's own address that entry is the selected one and the page is drawn with the area's menu (scenario 10). `TestNoMenuEntry.test_the_package_does_not_touch_the_menu_library` narrowed to `AppMenu` (decisions.md D2) | The two new tests fail before T008 |
| T008 | `mvp_compliance/menus.py` per plan.md *The menu entry*; `pyproject.toml` names `django-flex-menus>=0.4.5`; lock updated | T007 passes; `deptry` clean |
| T009 | Demo landing page links the list again. `docs/pages.md`: the list, what it shows, the folded history, whose records they are. `docs/models.md`: `of_agreed_documents()`. README feature list. `CHANGELOG.md` *Added*. `en` catalog regenerated | Docs check green; `makemessages` clean |

## US-2 — Knowing a newer version is in force (P2, issue #79)

| Id | Task | Done when |
|---|---|---|
| T010 | `tests/test_views.py::TestNewerVersionInForce` — a user whose latest acceptance is of a superseded version gets an entry whose `newer` is the version in force, and the page links to the document's address without `?version=` (scenario 1); a user who accepted the version in force gets `newer` of `None`, with and without earlier acceptances (scenarios 2, 3, SC-003); the response holds no form (scenario 4); publishing a version after a first request makes the second request carry `newer`, with nothing else done (scenario 5); the query count is unchanged from T005's | Fails before T011 |
| T011 | `mvp_compliance/views.py` — `newer` per plan.md *The view* | T010 passes; full suite green |

## US-3 — A project that leaves part of it out (P3, issue #80)

| Id | Task | Done when |
|---|---|---|
| T012 | `tests/test_views.py::TestWithoutTheAccountArea`, under a URLconf that mounts only the package's pages — system checks pass; a document page answers 200 and holds no link to the list; the list's address answers 404 for a signed-in user and for an anonymous one (scenario 2, FR-013, SC-007). `tests/test_menus.py::TestWithoutThePackagePages`, under a URLconf that mounts only `mvp.urls` — the processed `AccountCenterMenu` has no entry for the list, and the area's landing page answers 200 (scenario 3). With both mounted and no setting changed, the entry and the page are present (scenario 1, FR-012, SC-006: covered by T005 and T007, named here) | The 404 tests fail before T013 |
| T013 | `mvp_compliance/views.py` — `dispatch()` answers "not found" without the account area | T012 passes |
| T014 | `tests/test_models.py::TestReservedSlug` — `full_clean()` on a document with the slug `agreed` raises on `slug` with code `reserved`; the admin's add form refuses it and saves nothing (scenario 4). `tests/test_urls.py::TestFixedRoutes` — every fixed route in the package's URLconf has its segment in `Document.RESERVED_SLUGS`; with a document created from code under the slug `agreed`, the list's address still serves the list (FR-014) | Fails before T015 |
| T015 | `mvp_compliance/models.py` — `Document.RESERVED_SLUGS`, `unreserved_slug` on `Document.slug`; migration `0009` from `makemigrations` | T014 passes; `makemigrations --check` clean; full suite green |
| T016 | `docs/pages.md`: what a project mounts for the page to appear, and that it is absent, with nothing else changed, when either part is missing (FR-018). `docs/models.md`: the reserved slug. `CHANGELOG.md`: the slug `agreed` is no longer available, and a document already published under it stops being reachable. `en` catalog regenerated | Docs check green; `makemessages` clean |
