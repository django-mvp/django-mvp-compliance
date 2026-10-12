
## 2026-10-12T10:33:18Z · Orchestrator · plan

Research, plan and tasks written against main at 72fb4c0, which carries FS-009 as delivered. The FS-010 spec was read against FS-009's and nothing contradicts: the three amendments it makes to FS-009 are the ones FS-009's own decisions D16 and D22 left for it. Stories are built in dependency order: US-2, US-1, US-3, then US-4 to US-6 together (decisions.md D17). Next: design review.

## 2026-10-12T10:50:34Z · Implementer US2 · T002

Did: wrote TestEnforcement (tests/test_models.py) and TestEnforcedColumn (tests/test_migrations.py), tests first. Both classes are red on purpose until T003.
Verified: uv run pytest tests/test_models.py::TestEnforcement -q -> 11 failed (no `enforced` field, no enforced_outstanding_for); uv run pytest tests/test_migrations.py::TestEnforcedColumn -q -> 1 failed at the assertion that the document is enforced; pre-commit on both files passes.
Next: T003, the field, queryset method, migration 0002, docs/models.md and catalog.
Watch: the add/remove of the field changes what makemigrations --check sees, so T003 must carry the migration in the same commit. The brief file lacks a trailing newline, so pre-commit --all-files rewrites it; left alone as out of scope.

## 2026-10-12T10:52:39Z · Implementer US2 · T003

Did: Document.enforced (BooleanField, default True, with verbose_name and help_text), DocumentQuerySet.enforced_outstanding_for() and the forwarding DocumentManager method, migration 0002_document_enforced (one AddField, no RunPython), docs/models.md (a section on enforcement and one on enforced_outstanding_for() beside Outstanding), and the en catalog regenerated. makemessages marked the new "enforced" entry fuzzy with the translation "In force"; set it to the string itself and gave the help text its identical msgstr, like its neighbours.
Verified: uv run pytest tests/test_models.py::TestEnforcement tests/test_models.py::TestModelFields tests/test_migrations.py -q -> 37 passed. Mutation probe: dropping .filter(enforced=True) made test_leaves_out_a_document_that_is_not_enforced fail. makemigrations --check --dry-run -> No changes detected. makemessages run a second time leaves the catalog unchanged apart from its creation date.
Next: T004, the admin tests.
Watch: BLOCKED ON ONE PRE-EXISTING TEST. tests/test_models.py::TestDocument::test_document_holds_no_wording asserts the concrete fields of Document are exactly {id, name, slug, kind}, so it fails for any new field. It is not mine to change; the one-line edit it needs is to add "enforced" to that set. Everything else in tests/test_models.py and tests/test_migrations.py passes.

## 2026-10-12T10:53:50Z · Implementer US2 · T004

Did: TestDocumentEnforcement in tests/test_admin.py: the add form saves a document as enforced when the field is left as rendered and as not enforced when it is cleared; the change form switches enforcement off and on for a document with two published versions and two acceptances and leaves them as they were; the list has a field-enforced cell on the row of each document, found by its name, and the two cells differ.
Verified: uv run pytest tests/test_admin.py::TestDocumentEnforcement -q -> 1 failed, 3 passed. The changelist test fails at the missing cell (both rows found, no field-enforced cell), which is T005's. The three form tests pass already, because the model field of T003 brings the field onto the admin form with no admin change. My first run of them failed because the posts left out the required kind; fixed in the tests, no other change (2 attempts).
Next: T005, enforced in DocumentAdmin.list_display, then the glossary, the seed and the changelog.
Watch: tests/test_models.py::TestDocument::test_document_holds_no_wording still fails, as recorded under T003.

## 2026-10-12T10:56:02Z · Implementer US2 · T005

Did: `enforced` in DocumentAdmin.list_display after kind; the Enforcement entry in CONTEXT.md (set on the document, enforced when created unless chosen otherwise, takes effect only on a site that has switched the check on); seed_demo marks House rules not enforced by an update at the end of handle(); CHANGELOG Added; docs/authoring.md, which describes the documents list and the document's form, now names the Enforced column and field. decisions.md D19 records the seed choice and the test below.
Verified: uv run pytest tests/test_admin.py::TestDocumentEnforcement -q -> 4 passed. Full verify (forge verify --repo . --base origin/main) -> conformance passed, docs passed, typecheck passed, build passed, lint FAILED, test FAILED. Test: 1 failed, 593 passed at the first failure; a second run with no early stop gave 1 failed, 597 passed. The one failure is tests/test_models.py::TestDocument::test_document_holds_no_wording, which lists the concrete fields of Document and so fails for the new one. Lint: end-of-file-fixer rewrites specs/010-site-wide-agreement-check/US2-brief.json, which is committed without a final newline; ruff, ruff-format, mypy and deptry pass. makemigrations --check -> no changes. makemessages -l en --no-obsolete run again leaves only its creation date moved.
Next: nothing in this story. Needs Forge: the one-line edit to the field set in that test, and a final newline on US2-brief.json.
Watch: T003 and T005 are reported blocked on that single test and not recorded done in the ledger; their code is committed.

## 2026-10-12T11:04:42Z · Implementer US1 · T006

Did: tests/test_middleware.py (TestAgreementCheck, TestAgreementCheckOff, TestAgreementCheckCost), tests first. The module is its own URLconf and mounts the package, django-mvp and the admin, with a view that records being called; tests/urls_own_agree_page.py routes the page that asks to a view outside the package's namespace. The middleware is added with modify_settings; tests/settings.py and tests/urls.py are unchanged. The key the check writes is found by comparing the session before and after a request, so no test names it.
Verified: uv run pytest tests/test_middleware.py -q -> 36 failed, 1 passed: ModuleNotFoundError for mvp_compliance.middleware, which does not exist yet. To separate set-up faults from missing behaviour I ran the file once against a throwaway pass-through class (not committed, deleted): 21 failed and 16 passed, each failure at the assertion that the request was redirected, answered with HX-Redirect or remembered. My first run of it showed my own view took no route kwargs; fixed in the test module (2 attempts). TestAgreementCheckOff passes before and after by design. pre-commit run --all-files passes.
Next: T007, mvp_compliance/middleware.py.
Watch: the tests that pass against a pass-through (the reachable pages, sign-out, unmounted pages, ahead-of-user) are only meaningful once T007 exists; T007 probes each by removing the mechanism.

## 2026-10-12T11:09:40Z · Implementer US1 · T007

Did: mvp_compliance/middleware.py, one class: AgreementMiddleware with __init__, __call__ (steps 1, 2, 4, 6, 7 of plan.md), is_reachable() and the small methods it uses. The delay and the session key are module constants. Three tests added to T006's classes after mutation probes: an address that only starts like STATIC_URL, a scheme-relative STATIC_URL, and a finding dated in the future. decisions.md D20 records the two readings that plan.md leaves open.
Verified: uv run pytest tests/test_middleware.py -q -> 40 passed. Mutation probes, each run against the whole file and each killed unless named: removing the resolve/app_names/sign-out clause, the page-path equality, the static and media clause, the off-site guard, the site-root guard, the anonymous guard, the missing-user guard, the unmounted guard, remembering, writing, writing for a stopped user, storing a datetime, the number check, the path-segment rule, percent-encoding, and each of the three HX-Redirect rules. Two survived the first pass (the host test of urlsplit, and the segment rule) and are now killed by the two added tests; dropping the lower bound of the delay comparison is killed by the third. pre-commit run --all-files passes.
Next: T008, tests for the two system checks.
Watch: the check reads request.session directly, so a project with no sessions fails on a signed-in request (D14 revisit). tests/urls.py and tests/settings.py are unchanged: the middleware test module is its own URLconf, and tests/urls_own_agree_page.py serves the case of the page routed outside the package.

## 2026-10-12T11:11:14Z · Implementer US1 · T008

Did: tests/test_checks.py::TestAgreementChecks. run_checks() is read for the ids of this package's two checks only, with MIDDLEWARE set by override_settings and the package's pages unmounted by the urls marker (tests.urls_mvp_only). A subclass of AuthenticationMiddleware is defined in the test module and listed by its dotted path. A baseline test says a correct configuration reports neither.
Verified: uv run pytest tests/test_checks.py -q -> 3 failed, 3 passed. The three failures are the ones that expect E001 or E002 and get an empty set, because no check is registered; the three that pass expect nothing (the baseline, the subclass, the middleware absent) and are meaningful only once T009 exists, so T009 probes each. pre-commit run --all-files passes.
Next: T009, mvp_compliance/checks.py, registered from MvpComplianceConfig.ready().
Watch: the messages and hints are not asserted. Run_checks() also returns Django's own admin errors when AuthenticationMiddleware is missing; the test keeps only this package's ids.

## 2026-10-12T11:12:07Z · Implementer US1 · T009

Did: mvp_compliance/checks.py with one registered function, check_agreement_middleware(), which returns nothing unless AgreementMiddleware is listed, then mvp_compliance.E001 when reverse("mvp_compliance:agree") fails and mvp_compliance.E002 when no entry before the check is AuthenticationMiddleware or a subclass of it. MvpComplianceConfig.ready() registers it, importing it inside the method because the auth middleware's module needs the app registry. Messages and hints go through gettext; the include line and the two middleware paths are placeholders, so no msgid carries the package's module name. The en catalog regenerated and its four new entries given their own text as msgstr, like their neighbours.
Verified: uv run pytest tests/test_checks.py -q -> 6 passed (3 failed before). Probes, each killed by the named test: dropping the not-listed return (test_nothing_is_reported_while_the_middleware_is_not_listed), matching the exact class only (the subclass test), checking the whole list rather than the entries before (test_the_check_listed_ahead_of_authentication_is_an_error), dropping the reverse (the unmounted test), not registering (three tests). makemessages -l en --no-obsolete run a second time -> no difference. makemigrations --check --dry-run -> No changes detected. pytest tests -k "catalog or checks or app" -> 30 passed. pre-commit run --all-files passes.
Next: T010, docs/enforcement.md, README, demo settings and CHANGELOG.
Watch: E003 and the settings it guards belong to US-4 and US-5; the function has a place to take it.

## 2026-10-12T11:15:37Z · Implementer US1 · T010

Did: docs/enforcement.md (new): switching the check on and where it goes, what it does to a signed-in person step by step, that a visitor who is not signed in is never touched, what stays reachable and how "beneath" is read, a submission and a request for part of a page (htmx's HX-Request, HX-Redirect and HX-Boosted by its documented behaviour, a boosted link keeping its return address), the sixty-second delay and what follows from it, what the middleware costs a project (the user and session read on every request, Vary: Cookie, measured), and E001 and E002. README: the scope bullet, an installation step, the documentation index. demo/settings.py: the middleware after AuthenticationMiddleware. CHANGELOG Added. docs/pages.md: one paragraph said nothing sends anyone to the page, which is no longer true once the middleware is listed; changed that paragraph only. Before this task the middleware was cut down to __call__ and is_reachable() (commit "T007: keep the middleware to __call__ and is_reachable", behaviour unchanged, T007's tests green); the docs gate wants every public name quoted as code, and the plan names those two.
Verified: forge verify --repo . --base origin/main --steps docs -> passed. DJANGO_SETTINGS_MODULE=demo.settings django-admin check -> no issues. A throwaway request through the test client showed Vary: Cookie on an anonymous response with the middleware listed and none without (file deleted). pre-commit run --all-files passes.
Next: the full verify, once, then the report.
Watch: README's status block still says "No account-area page exists yet", which was already out of date before this story and is not touched here. The demo's landing page and its own agreement view are US-3's and US-4's; with the middleware on, a demo user with an enforced document outstanding is sent to the agreement page from the landing page until those land.

## 2026-10-12T11:21:21Z · Implementer US3 · T011

Did: tests/test_views.py::TestAgreementEnforcement, 19 tests (with the parametrised cases), without the middleware except the last one. Enforced and unenforced documents come from two fixtures; the submission helper lists and agrees to the versions named. Covers scenarios 1 to 11 and the Independent Test: agreeing to the enforced document only, to both, to one of two enforced, to the unenforced only; the entries' `optional` flags; the required entries equal to `enforced_outstanding_for(user)`; a visit with only an unenforced document outstanding, with a path, a foreign host and an empty `next`, and without one; a submission agreeing to it or to nothing; nothing outstanding; a failing write; enforcement switched off and on after the page was drawn; and the whole path through AgreementMiddleware to the account area. Added `modify_settings` to the module's django.test import.
Verified: uv run pytest tests/test_views.py::TestAgreementEnforcement -q -> 10 failed, 9 passed. The ten failures are the ones that treat an unenforced document as required (200 where 302 is expected, `optional` false where true is expected, an extra entry in the required set); the nine passes are guards that hold today and must keep holding after T012. pre-commit run --files tests/test_views.py passes.
Next: T012, mvp_compliance/views.py and the demo.
Watch: the page's `?next=` rule is tested with an empty value as well as a path and a foreign host, so `get()` has to test for the parameter's presence rather than a truthy value.
