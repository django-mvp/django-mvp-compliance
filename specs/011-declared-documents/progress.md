
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
