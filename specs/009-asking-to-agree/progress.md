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
