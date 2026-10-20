
## 2026-10-20T12:58:11Z · Implementer US1 · T001

Did: wrote TestCreateDeclaredDocuments (14 tests) before any code; red = ModuleNotFoundError for mvp_compliance.management.
Verified: uv run pytest tests/test_management.py -q -x, collection error as expected.
Next: T002.
Watch: no test for the router-refusal branch, the test settings have one database and no router.

## 2026-10-20T12:58:11Z · Implementer US1 · T002

Did: declared_documents(), mvp_compliance/management.py create_declared_documents (steps 1, 2, 5), connected in ready(); migrate wiring test in test_app.py (red first: document not created).
Verified: uv run pytest tests/test_management.py tests/test_app.py -q: 20 passed; pre-commit run --all-files clean.
Next: T003.
Watch: pre-commit end-of-file hook rewrites specs/.../US1-brief.json; restored, not committed.

## 2026-10-20T13:01:00Z · Implementer US1 · T003

Did: refusal tests first (9 red: not raised / IntegrityError), then declaration_faults and the refusal in create_declared_documents, catalog regenerated (stable on a second run).
Verified: uv run pytest tests/test_management.py tests/test_app.py -q: 31 passed.
Next: T005.
Watch: a non-string name would raise AttributeError in the strip check.

## 2026-10-20T13:01:00Z · Implementer US1 · T004

Did: T004 as above, no separate behaviour beyond T003.
Verified: uv run pytest tests/test_management.py -q: 25 passed; makemessages en clean.
Next: T005.
Watch: none.

## 2026-10-20T13:01:01Z · Implementer US1 · T005

Did: docs/models.md Declaring documents, docs/pages.md, README, CONTEXT, CHANGELOG, demo settings, seed_demo sets kind after its early return.
Verified: migrate then seed_demo on an empty demo database leaves Impressum kind=notice with 1 version; makemigrations --check clean.
Next: full verify and report.
Watch: demo.sqlite3 was moved aside for the check and restored.

## 2026-10-20T13:08:58Z · Implementer US2 · T006

Did: tests first. TestDeclaredSlug (models), TestDeclaredDocumentAdmin (admin) and two exception tests.
Verified: uv run pytest on the three scopes; 7 failed for the right reason (no raise, slug input still rendered), 18 passed.
Next: T007, the lock, the admin condition, docs, catalog.
Watch: bulk_update tests need their own transaction.atomic() savepoint, as the existing ones do.

## 2026-10-20T13:08:58Z · Implementer US2 · T007

Did: DeclaredDocumentError; the declared check in Document.save() and DocumentQuerySet.update() before the published check; DocumentAdmin.get_readonly_fields; docs/models.md, CONTEXT.md, ADR 0019, CHANGELOG; en catalog.
Verified: scoped tests 47 passed; pre-commit all hooks passed; makemessages run, new string given its msgstr like its neighbours.
Next: full verify and report.
Watch: the T006 bulk_update test needed a savepoint, fixed in this commit.
