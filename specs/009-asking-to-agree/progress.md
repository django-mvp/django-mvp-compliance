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
