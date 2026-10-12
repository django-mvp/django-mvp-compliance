# Progress — 009 Asking a signed-in person to agree to what is outstanding

## 2026-10-12T08:41:00Z · Orchestrator · T001

Did: removed the prototype view, route, reserved slug and demo fakes; kept the templates, the row component, the script and the seed. Widened the string tests to the new template and the component. Catalog regenerated.
Verified: forge verify --base origin/main, all six steps green (292 tests).
Next: design review, then US-1.
Watch: the demo landing card names the accounts but has no link until T006 restores the route.

## 2026-10-12T08:54:36Z · Implementer US1 · T002

Did: added TestRecordMany to tests/test_models.py: one acceptance per version with user, subject and time; a version already accepted passed over and unchanged; a draft or a notice's version refused with nothing written, the rest of the batch included; the optional address follows the setting; an empty batch writes nothing; the query count is the same for one version as for five.
Verified: uv run pytest tests/test_models.py::TestRecordMany -q, 8 failed, every one with AttributeError: 'AcceptanceManager' object has no attribute 'record_many'. uv run pre-commit run --all-files green.
Next: T003, record_many() on AcceptanceManager.
Watch: the red state is deliberate and ends with T003.

## 2026-10-12T08:55:23Z · Implementer US1 · T003

Did: AcceptanceManager.record_many(user, versions, request=None) in models.py, beside record(): refuses a draft before touching the database, takes the subject from Acceptance.subject_of(user), builds one Acceptance per version with a shared time and the address the setting allows, and writes them with the queryset's bulk_create(ignore_conflicts=True), which refuses a notice's version for the whole batch. docs/models.md: a section on record_many(), that it sends no save signals and needs a database that can ignore conflicts (not Oracle); the other passages that named record() as the only route now name it too.
Verified: uv run pytest tests/test_models.py::TestRecordMany tests/test_models.py::TestRecording tests/test_models.py::TestOptionalEvidence -q, 31 passed. uv run pre-commit run --all-files green. No new string: the refusal message is record()'s own.
Next: T004, the view's tests.
Watch: the address lookup is written twice, in record() and record_many(); record() was left as it was on purpose.

## 2026-10-12T08:56:56Z · Implementer US1 · T004

Did: added TestAgreement to tests/test_views.py with its helpers: the entry for one outstanding document and its version in force; the link to that version's page; none of the stored HTML on the page; one acceptance and the redirect to next; a GET records nothing; nothing agreed records nothing and sets missing; an anonymous GET goes to sign-in carrying the page's full address; a superseded acceptance leaves the version in force listed and agreeing makes two; a notice and a draft-only document not listed; the same agreement twice leaves one; superseded, draft, already-accepted, notice and non-numeric ids record nothing; a post without a CSRF token is 403; the address follows the setting; markup in a name is escaped; a destination off the site, another scheme or protocol-relative becomes /; the form id, data-required, aria-describedby targets and the script.
Verified: uv run pytest tests/test_views.py::TestAgreement -q, 20 failed, every one NoReverseMatch for 'agree' (the route does not exist yet). uv run pre-commit run --all-files green.
Next: T005, AgreementView and the agree/ route.
Watch: the tests have not yet run against a rendered page, so any mistake in how they read the markup shows at T005.

## 2026-10-12T08:59:13Z · Implementer US1 · T005

Did: AgreementView in views.py: get_entries(), is_optional() answering False, get(), post() reading the outstanding entries, matching submitted agree values as strings against their version ids, writing once through record_agreed() inside transaction.atomic(), reading the entries again and going on only when none is required, get_destination() keeping next only for the request's host and scheme and otherwise /, and get_context_data() supplying the entries with their field attributes, required_count, destination and redirect_field_name. dispatch is wrapped with csrf_protect. urls.py routes agree/ ahead of the slug route. en catalog regenerated.
Verified: uv run pytest tests/test_views.py tests/test_app.py -q, 134 passed (TestAgreement 21 of them). Probe: with the csrf_protect decorator removed, test_the_refusal_holds_in_a_project_running_no_csrf_middleware fails with 302 for 403; restored. uv run pre-commit run --all-files green. makemessages -l en --no-obsolete run; only the view's three strings and line references changed.
Next: T006, the strings test, the demo link and the documentation.
Watch: I loosened one of my own T004 assertions: the shell draws a logout form as well, so the test looks for the agreement form among the page's forms. No failure handling, no changed notice and no redirect for a person with nothing outstanding yet; those are US-2 to US-4.

## 2026-10-12T09:00:28Z · Implementer US1 · T006

Did: TestAgreementStrings in tests/test_views.py (the rendered page, title and trail included, holds none of the forbidden words); the demo landing page links the page again; docs/pages.md gains "Asking a person to agree" (what it lists, what a submission records, where the person goes, who may use it, that it stops nobody) with the route in the address table and the template in the overriding table; README feature bullet and documentation entry; CHANGELOG Added for the page and record_many().
Verified: uv run pytest tests/test_views.py::TestAgreementStrings tests/test_views.py::TestPageStrings -q, 15 passed. Probe: with "Compliance" put in the page title the new test fails; restored. makemessages -l en --no-obsolete leaves the catalog unchanged. uv run pre-commit run --all-files green.
Next: full verify, then the report.
Watch: the demo landing card still describes the unrecorded.user and optional accounts, which need the demo's own view from US-2 and US-3; today those accounts behave like any other.

## 2026-10-12T09:06:24Z · Implementer US2 · T007

Did: Added TestAgreementNotRecorded to tests/test_views.py (8 cases across DatabaseError and RecordError): failed write answers 200 with `failed` set, nothing recorded and the document still outstanding; submitted-on toggles come back checked; a second submission with the write working goes on to the first destination; the failure is logged on mvp_compliance.views at error level with the exception attached and its message absent from the page; a write that stores nothing and raises nothing does not let through; a write that stores three then raises keeps none.
Verified: `uv run pytest tests/test_views.py::TestAgreementNotRecorded -q` -> 7 failed, 1 passed. The seven fail because the DatabaseError / RecordError escapes post() (the right reason). The passing one is the no-error-nothing-stored case, which the US-1 view already satisfies by reading the records after the write. `uv run pre-commit run --all-files` green.
Next: T008, the failure branch and the transaction in AgreementView.post(), the demo view and route, docs/pages.md.
Watch: none.

## 2026-10-12T09:08:45Z · Implementer US2 · T008

Did: AgreementView.post() now wraps the write in `transaction.atomic()` inside a `try`, with the `except (DatabaseError, RecordError)` outside the block: it logs with `logger.exception` on mvp_compliance.views and draws the page with `failed`; get_context_data keeps the toggles that were submitted on (`checked`) after a failure, matching submitted values as strings. demo/views.py gains DemoAgreementView (record_agreed raises DatabaseError for unrecorded.user@example.com) and demo/urls.py routes legal/agree/ to it ahead of the include. docs/pages.md: what happens when an acceptance cannot be stored, and the logger to attach error reporting to. Catalog regenerated; only reference line numbers moved.
Verified: `uv run pytest tests/test_views.py -q` all green; TestAgreementNotRecorded 8 passed. Probes: removing atomic() fails the write-all-then-fail test; letting through after a no-op write fails the no-error test. A throwaway script on demo.settings: unrecorded.user got 200 and no acceptance, another user 302 and one acceptance. `uv run pre-commit run --all-files` green.
Next: full verify once, then the report.
Watch: the demo's `is_optional` is not added: that is the next story.

## 2026-10-12T09:15:02Z · Implementer US3 · T009

Did: wrote TestSeveralOutstanding in tests/test_views.py, 14 tests covering the story's seven scenarios, the query counts and the rows a view marks optional. Optional rows are reached by patching AgreementView.is_optional with monkeypatch.
Verified: `uv run pytest tests/test_views.py::TestSeveralOutstanding -q` gives 2 failed, 12 passed. The two failures are the `changed` cases (a version replaced, and a document published, after the page was drawn): `changed` is never set in the context, so the page is drawn with `missing` instead. The 12 that already passed were each probed by breaking the mechanism in views.py and restoring it: dropping order_by("name"), agreeing only the first version, a fixed "/" destination, ignoring outstanding_for, a query per document, a write per version, data-required on every toggle, never redirecting on all-optional, ignoring is_optional, not recording an optional agreement, and linking the first version instead of the current. Every one of the 12 failed under at least one probe.
Next: T010, step 2 of post() sets `changed` and the page is drawn without `missing`; the demo's is_optional.
Watch: required-first sorting is already in get_entries() from T005 and has no test, by rule, so T010 changes nothing there.

## 2026-10-12T09:16:39Z · Implementer US3 · T010

Did: post() reads the submitted `listed` values and sets `changed` when an entry read at submission has a version id absent from them; the page is then drawn with `changed` and without `missing`. DemoAgreementView.is_optional() answers from DEMO_OPTIONAL_DOCUMENT_SLUGS = ["house-rules"] in demo/settings.py. docs/pages.md describes partial agreement, the changed list and the `changed` context key. D21 records why the check uses the first read.
Verified: `uv run pytest tests/test_views.py::TestSeveralOutstanding tests/test_views.py::TestAgreement tests/test_views.py::TestAgreementNotRecorded tests/test_views.py::TestAgreementStrings -q` gives 44 passed. `uv run pre-commit run --all-files` passes. `django-admin makemessages -l en --no-obsolete` leaves the tree clean: no string was added. The demo view was imported under demo.settings and answers true for house-rules and false for another slug.
Next: full verify, once, then the report.
Watch: entries were already sorted required first from T005, and nothing in T010 touches that. A version replaced in the instant of the write is not seen by `changed` (D19, D21); it still leaves the person on the page.

## 2026-10-12T09:21:13Z · Implementer US4 · T011

Did: wrote TestAgreementDestination in tests/test_views.py, 22 cases covering scenarios 1 to 7 of the story: a same-site destination, nothing outstanding on GET (302, empty body, no template), a foreign destination and no destination giving the configured default and not "/", the setting as a path and as a URL name, the page's own address in six forms, and the destination carried in the form after a failed write and after a partial agreement.
Verified: `uv run pytest tests/test_views.py::TestAgreementDestination -q` gives 16 failed, 6 passed. The 16 fail for the right reasons: the page is drawn (200) where a redirect is expected, and the destination is "/" or the page's own address where the project default is expected. The 6 that pass on the existing view (same-site destination, optional-only page still shown, site-root default, an address that only starts like the page, destination kept after a failed write, destination kept after a partial agreement) are probed by mutation after T012. `uv run pre-commit run --all-files` passes.
Next: T012, get_destination() per plan.md and the redirect in get() when nothing is outstanding; docs/pages.md, README settings, CHANGELOG.
Watch: the tests take the project default from a path, "/welcome/", so "/" cannot satisfy them by accident.

## 2026-10-12T09:24:28Z · Implementer US4 · T012

Did: get_destination() keeps a same-site next that is not the page's own address, otherwise resolve_url(MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL, default "/"); is_own_address() joins the value onto the request's path, unquotes its path and compares with trailing slashes ignored; get() redirects to the destination when nothing is outstanding. docs/pages.md gains "Sending a person to the page" (link and view example, how next is given, which addresses are followed, the setting, a person with nothing outstanding) and "Where the person goes" points to it. README settings and CHANGELOG Added. D22 records why a GET with only optional documents still draws the page.
Verified: `uv run pytest tests/test_views.py::TestAgreementDestination -q` gives 22 passed. Probed the six cases that passed before the change by breaking views.py and restoring it: always the default (6 fail), redirect on GET when all optional (1), site-root default changed (1), own address matched by prefix (1), next read from the query string only (4). The docs view example was run in a throwaway test against the branch: the link, the page, the agreement and the redirect for nothing outstanding all answer as written. `uv run pre-commit run --all-files` passes. `django-admin makemessages -l en --no-obsolete` only moved line references, committed. `uv run pytest tests/test_views.py -k "TestAgreement or TestSeveralOutstanding"` gives 1 failed, 65 passed.
Next: Forge triage of the one failing existing test; nothing else is pending in this story.
Watch: tests/test_views.py::TestAgreement::test_a_notice_and_a_document_with_only_a_draft_are_not_listed (T005, not authored in this story) does a GET for a person with nothing outstanding and reads response.context["entries"]. FR-018 and T011 scenario 2 make that GET a redirect, so no context exists. Both cannot hold for the same state and no code change satisfies both without special-casing, so the test was left as it is and T012 is not recorded done. A GET-then-POST would keep what it checks: the person is listed nothing and records nothing.

## 2026-10-12T09:30:44Z · Implementer US5 · T013

Did: wrote TestAgreementInAProject in tests/test_views.py (page renders in the shell with no project template; the project template at tests/project_templates/mvp_compliance/agreement.html is the one rendered; a submission built from that page's own fields records and redirects; under tests.urls_mvp_only the system checks pass and Acceptance.objects.record() works), one case in TestAgreement for a document created from code under the slug agree, and the reserved-slug cases in tests/test_models.py::TestReservedSlug and tests/test_admin.py::TestDocumentSlugInTheAdmin. The project template is a fixture that posts agree, listed, next and the CSRF token, marked with id project-agreement-page.
Verified: `uv run pytest tests/test_views.py::TestAgreementInAProject tests/test_views.py::TestAgreement tests/test_models.py::TestReservedSlug tests/test_admin.py -q` gives 2 failed, 136 passed. The two failures are the new slug tests: full_clean() does not raise (DID NOT RAISE ValidationError) and the admin add form answers 302 and saves the document. The six new view tests passed on first run and were each probed: a wrong template_name fails 4 of them, the slug route listed ahead of agree/ fails the same 4, a reverse of the package's address from a registered system check fails the checks case, and the same reverse inside record() fails the record case. Every mutation was restored with git checkout. `uv run pre-commit run --all-files` passes.
Next: T014, "agree" in Document.RESERVED_SLUGS, then the pages, CHANGELOG and CONTEXT.md.
Watch: tests/test_models.py::TestReservedSlug::test_a_slug_that_only_contains_the_reserved_one_is_valid has "agree" in its parameters and asserts it valid. It is not authored in this story and cannot hold together with the new reserved-slug case.

## 2026-10-12T09:32:49Z · Implementer US5 · T014

Did: "agree" added to Document.RESERVED_SLUGS (one member, comment updated). docs/pages.md: the address section now says both `agreed` and `agree` are refused and what becomes of a document already published under `agree`; the agreement.html row of the template table names every context key (entries with document, version, optional, field; required_count; destination; redirect_field_name; failed; missing; changed); new "Replacing the page that asks" (what the form must send, the field's attributes, the Cotton row component, the script's three hooks) and "Changing how an agreement is stored" (record_agreed(), a view override mounted ahead of the include, what a DatabaseError or RecordError does). is_optional() is not documented. docs/models.md and CHANGELOG: the slug `agree` is no longer available and a document published under it stops being reachable. CONTEXT.md: Outstanding.
Verified: `uv run pytest tests/test_models.py::TestReservedSlug tests/test_admin.py::TestDocumentSlugInTheAdmin -q` gives 1 failed, 10 passed: both new slug tests pass; the failure is the existing test_a_slug_that_only_contains_the_reserved_one_is_valid[agree], which asserts `agree` is a valid slug. `uv run python manage.py makemigrations --check --dry-run` prints "No changes detected", exit 0. `uv run pre-commit run --all-files` passes. makemessages leaves only line references moved in the en catalog, committed. The two template examples and the view override in docs/pages.md were run against the branch in a throwaway test (removed): the page rendered from the documented template posts agree, listed, next and the token, records and redirects, the Cotton row posts the same, and the overriding view's record_agreed() runs once.
Next: Forge triage of the one existing test. T014 is not recorded done.
Watch: tests/test_models.py::TestReservedSlug::test_a_slug_that_only_contains_the_reserved_one_is_valid lists "agree" among the valid slugs. It was not authored in this story and reserving the slug makes it fail, so it was left as it is. The fix is to drop "agree" from its parameters; the new case beside it is the one that covers "agree".

## 2026-10-12T09:37:43Z · Orchestrator · converge

Did: converged. Two decision records (0021, 0022), a verdict on each of 24 decisions, links from docs. Triage of two earlier tests recorded (D23, D24). No migration. Dev database reseeded.
Verified: forge verify --base origin/main, six steps green. tamper-check against main flags the two test edits recorded in tasks.md T001 and decisions.md D24.
Next: code review.
Watch: none.
