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
