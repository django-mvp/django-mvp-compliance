# Progress — 008 What a person has agreed to, in their account area

The running log of this feature's implementation run. The ledger (`feature-state.json`) is the
machine record; this is the readable one.

---

## 2026-10-01 — Prototype

The specification was approved by review on #77. No feature had been delivered since it was
written, so there was nothing to re-read it against. A prototype of the page was built on this
branch and reviewed on the running demo. Review changed the menu entry's label, moved the document
page's list into a pinned card in its own column, and folded long histories. The prototype was
approved the same day. What it needs from the code and what it faked are in `sketch.md`.

## 2026-10-01 — Plan

Research, plan and tasks written against `origin/main` at `33eb41a`. The specification is marked
refined for the two changes that came out of the review (decisions.md D1, FR-019). Three stories,
run in sequence after a foundational step that removes the prototype's untested Python so it is
rebuilt behind failing tests. Every functional requirement and success criterion maps to at least
one task.

The suite on the prototype commit: 437 passed, 6 failed. All six are accounted for in the tasks:
the menu test narrowed in T007 (decisions.md D2), and five string and catalog tests fixed in T001.

## 2026-10-01 — Design review

One reviewer, three lenses. Verdict: changes requested, on one high finding about the test helpers
for translated strings, which could not read a plural. Six findings in all, none against the
specification and none on security. All six were applied as edits to the plan and tasks
(decisions.md D6). Each premise the plan rests on about django-mvp and its menu library was checked
against the installed packages and holds.

## 2026-10-01 — Plan passed; groundwork

The plan was passed as written. T001: the prototype's view, route and menu entry are removed, the
demo's link to the list with them. The two helpers behind the string tests read plural entries, and
the `en` catalog is regenerated for the three page templates: fourteen strings added, none removed
or changed. T002: `docs/pages.md` and the changelog describe the document page's new layout and the
custom property for the card's offset. Full suite: 443 passed.

## 2026-10-01T21:30:00Z · Implementer US1 · T003

Did: `tests/test_models.py::TestAcceptancesOfAgreedDocuments`, five tests (six cases): own records of documents people agree to only, ordering by document name then newest published first, a version never accepted between two accepted ones is absent, a document made a notice drops out and returns (`save` and `update` routes), one query with version and document loaded.
Verified: `uv run pytest tests/test_models.py::TestAcceptancesOfAgreedDocuments -q` gives 6 failed, all `AttributeError: 'AcceptanceQuerySet' object has no attribute 'of_agreed_documents'`.
Next: T004 adds the method and the manager forwarder.
Watch: none.

## 2026-10-01T21:40:00Z · Implementer US1 · T004

Did: `AcceptanceQuerySet.of_agreed_documents()` and the `AcceptanceManager` forwarder, as plan.md gives them. Fixed a fault in my own T003 helper: it published identical wording twice for one document, which the model refuses (PublishError), a failure the red run had hidden behind the AttributeError. Each call now publishes distinct wording. No assertion changed.
Verified: `uv run pytest tests/test_models.py::TestAcceptancesOfAgreedDocuments -q` gives 6 passed. Probes: the kind filter replaced by `all()` fails the two notice cases; `-version__published_at` flipped fails the ordering and skipped-version tests. `uv run ruff check` and `ruff format --check` clean.
Next: T005 view tests.
Watch: the first test's notice has no acceptance (none can be recorded against one), so notice handling is tested through the kind-change cases.

## 2026-10-01T22:00:00Z · Implementer US1 · T005

Did: `tests/test_views.py::TestAgreedDocuments`, 22 cases covering the scenarios listed in tasks.md T005 (records and ordering, links to `?version=`, own records only for people and staff, nothing appended to the address, nothing in the query string naming a person, empty page, anonymous redirect, notice and never-accepted documents absent, rename, escaping, the three-and-rest fold at five and none at four, query count for one acceptance against fifty across ten documents, nothing written, POST 405). The test URLconf now mounts `mvp.urls` at the root, and `tests/settings.py` sets `LOGIN_URL = "account_login"` so the anonymous redirect has a target.
Verified: `uv run pytest tests/test_views.py::TestAgreedDocuments -q` gives 21 failed, 1 passed. All 21 failures are `NoReverseMatch: Reverse for 'agreed' not found`. The pass is the test that follows a version link on the existing document page.
Next: T006 view, route and catalog.
Watch: `test_following_a_link_serves_that_versions_stored_html` passes before T006 by design: it exercises the document page that already exists.

## 2026-10-01T22:25:00Z · Implementer US1 · T006

Did: `AgreedDocumentsView` (sign-in required, GET and HEAD only, `get_entries()` grouping each document's acceptances into `shown` and `earlier` with `newer` always `None`), the `agreed/` route ahead of the slug route, and the `en` catalog regenerated for the title, subtitle and "Account Center". One fault in my own T005 test fixed: it asserted a version's status from a stale in-memory object, so it now refreshes it first; no assertion changed.
Verified: `uv run pytest tests/test_views.py::TestAgreedDocuments -q` gives 22 passed; `uv run pytest -q` gives 471 passed. Probes: removing `LoginRequiredMixin` fails the anonymous test; calling `of_agreed_documents()` on every acceptance instead of the person's fails the staff and query-string tests; folding at four instead of five fails the four-versions test. Adding `post` to `http_method_names` fails nothing, because `TemplateView` has no `post` handler and refuses it with 405 either way.
Next: T007 menu tests.
Watch: the 405 test passes by the framework's own behaviour as well as by the explicit `http_method_names`.

## 2026-10-01T22:40:00Z · Implementer US1 · T007

Did: `tests/test_menus.py::TestAccountAreaEntry`, two tests: a signed-in request gets an entry whose address is the list's; on the list's own address that entry is selected and the page's menu is the account area's. `TestNoMenuEntry.test_the_package_does_not_touch_the_menu_library` narrowed as decisions.md D2 says: it now looks for `AppMenu` and `MobileFooterMenu` and no longer for `flex_menu`, which the menu module will import. Nothing else in that class changed.
Verified: `uv run pytest tests/test_menus.py tests/test_views.py::TestNoMenuEntry -q` gives 2 failed, 2 passed. Both failures are an empty list of entries named `agreed-documents`.
Next: T008 menu entry, dependency and catalog.
Watch: the entry is found by name in the processed menu's children; if T008 shows `children` is not the processed list, the helper changes, not an assertion.

## 2026-10-01T22:55:00Z · Implementer US1 · T008

Did: `mvp_compliance/menus.py` appends the "Agreements" entry (name `agreed-documents`, view `mvp_compliance:agreed`, icon `document`) to `AccountCenterMenu`. `pyproject.toml` names `django-flex-menus>=0.4.5` and `uv lock` records it. The comment on the `DEP002` ignore no longer says no module imports django-mvp. The `en` catalog gained the entry's label.
Verified: `uv run pytest tests/test_menus.py tests/test_views.py::TestNoMenuEntry -q` gives 4 passed; `uv run pre-commit run --all-files` passes every hook, deptry included; `uv run pytest -q` gives 473 passed.
Next: T009 documentation and the demo's landing page.
Watch: the `DEP002` ignore for django-mvp is kept as it was, with a comment that is now true. Whether it is still needed is not something this task asked about.

## 2026-10-01T23:05:00Z · Implementer US1 · T009

Did: the demo landing page links the list again (the saved card, after the "Writing and publishing a document" card). `docs/pages.md`: the list's address and view in the address table, a section on what the page shows, the folded history and whose records they are, the introduction and the menu section corrected to say the package adds nothing to the project's own menus and one entry to the account area's menu, the list's template in the override table, and the need to mount django-mvp's URLs. `docs/models.md`: `of_agreed_documents()`. README: the feature bullet and the pages.md entry. CHANGELOG: an *Added* entry.
Verified: `uv run python manage.py makemessages -l en --no-obsolete` leaves the catalog unchanged; `uv run python manage.py check` reports no issues; a test client request for the demo's landing page returns 200 with the link to `/legal/agreed/`.
Next: the full verify, then the report.
Watch: `newer` is documented as `None` on every entry, which is true until the next story.

## 2026-10-01 — US-1 accepted

Seven tasks, seven commits. Checked again independently on `df67f0c`: lint, types, tests, build and
the documentation check all pass. The check for edits to existing tests flagged one, the narrowing
of the menu test that decisions.md D2 authorises. The approved templates and stylesheet are
untouched.

## 2026-10-01T23:35:00Z · Implementer US2 · T010

Did: `tests/test_views.py::TestNewerVersionInForce`, eight tests. A latest acceptance of a superseded version gets `newer` as the version in force and the page links the document's plain address with no `?version=`; the version in force accepted, alone or after earlier ones, gives `None`; each document is judged on its own versions; another person's acceptance of the version in force does not count; the list part of the page holds no form; a version published between two requests shows on the second; the query count is the same for one acceptance as for fifty across ten documents, with a newer version present in both.
Verified: `uv run pytest tests/test_views.py::TestNewerVersionInForce -q` gives 4 failed, 4 passed. Each failure is `newer` being `None` where the version in force is expected. The four that pass (the two `None` cases, the no-form check and the query count) hold today because every `newer` is `None`; they guard T011.
Next: T011 sets `newer` in `get_entries()`.
Watch: the shell draws a sign-out form, so the no-form check reads only the page from the list's container onward.

## 2026-10-01T23:50:00Z · Implementer US2 · T011

Did: `AgreedDocumentsView.get_entries()` reads `Version.objects.current().filter(document__in=...)` once for the page and sets `newer` to the version in force when none of the person's acceptances of that document is of it; `None` otherwise. The docstring says so. `docs/pages.md` gained the statement about a newer version (what it says, when it shows, that it is read each request, that the page has no form) and the template table row for `newer` is corrected. The CHANGELOG entry from the first story gained a sentence.
Verified: `uv run pytest tests/test_views.py::TestNewerVersionInForce tests/test_views.py::TestAgreedDocuments -q` gives 30 passed. `uv run python manage.py makemessages -l en --no-obsolete` changes only the POT-Creation-Date line, reverted, so the catalog is unchanged. Pre-commit hooks pass on the changed files.
Next: the full verify, then the report.
Watch: a person with no acceptances issues no current-version query (an empty `__in`), one fewer than a person with any; the query-count test compares one acceptance with fifty, both with a newer version present.

## 2026-10-01 — US-2 accepted

Two tasks, two commits. Checked again independently on `5cd3f01`: lint, types, tests, build and the
documentation check all pass, and no existing test was changed.
