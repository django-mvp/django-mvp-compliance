# Progress — 001 Legal documents kept as versioned records

Run narrative. Newest entry last.

## 2026-09-21 — S3 PLAN

Picked off the feature queue as the only row reporting `ready`. The specification merged to main in
pull request #6 at 17:29 UTC and the issue graph was already built: epic #4, stories #7 to #11. No
feature has been delivered in this repository since the specification landed, so the specification
was not re-read against later ones.

Baseline verified green on `1f56542` before anything was written: lint, typecheck, test, build and
conformance all pass.

Written this stage: `research.md`, `plan.md`, `tasks.md`, this file and `feature-state.json`.
`decisions.md` gained D8, D9 and D10 — the three ambiguities the plan had to settle that the
specification did not reach.

The design in one line: two models, publishing as a method that renders once and freezes the row,
"one version in force" as a partial unique index rather than application logic, and immutability
enforced on all four write routes with the manager declared `use_in_migrations` so a migration gets
the same refusal.

## 2026-09-21T22:58:54+02:00 · Implementer US-1 · T010

Did: added `TestDocument` with the three-documents-coexist and duplicate-name tests.
Verified: `poetry run pytest tests/test_models.py::TestDocument` — collection error,
`ModuleNotFoundError: No module named 'mvp_compliance.models'` (right reason: Document
doesn't exist yet).
Next: T011.
Watch: nothing.

## 2026-09-21T22:59:04+02:00 · Implementer US-1 · T011

Did: added `test_document_holds_no_wording`, asserting Document's concrete field set is
exactly `{"id", "name"}`.
Verified: same scope, same `ModuleNotFoundError` (unchanged — right reason).
Next: T012.
Watch: nothing.

## 2026-09-21T22:59:23+02:00 · Implementer US-1 · T012

Did: built `Document` — `name` only, unique, `verbose_name`/`help_text`, `Meta`, `__str__`.
Verified: `poetry run pytest tests/test_models.py::TestDocument` — 1 passed
(`test_document_holds_no_wording`, no DB access), 2 failed with
`OperationalError: no such table: mvp_compliance_document`. Expected: no migration exists
yet (T017). `poetry run pre-commit run --files mvp_compliance/models.py` clean.
Next: T013.
Watch: the two DB-backed `TestDocument` tests stay red until T017 lands the migration —
this is the correct order per the brief's task list, not a defect.

## 2026-09-21T22:59:37+02:00 · Implementer US-1 · T013

Did: added `TestVersion` — versions numbered in order, independent per document, and a
test forcing a number collision via `bulk_create` (bypassing `save()`'s auto-assignment)
to prove the database constraint holds.
Verified: `poetry run pytest tests/test_models.py::TestVersion` — collection error,
`ImportError: cannot import name 'Version'` (right reason: Version doesn't exist yet).
Next: T014.
Watch: nothing.

## 2026-09-21T22:59:57+02:00 · Implementer US-1 · T014

Did: built `Version` — `document` (`PROTECT`, `related_name="versions"`), `number`
(assigned in `save()` as `max+1` within the document whenever the row is new, via
`self._state.adding`), `markdown`. `Meta.ordering = ["document", "number"]`,
`unique_version_number_per_document`.
Verified: `poetry run pytest tests/test_models.py` — 1 passed, 4 failed, all
`OperationalError: no such table` (same expected reason as T012, pending T017).
`poetry run pre-commit run --files mvp_compliance/models.py` clean.
Next: T015.
Watch: same as T012's — resolves at T017.

## 2026-09-21T23:00:17+02:00 · Implementer US-1 · T015

Did: added `DocumentFactory` and `VersionFactory` to `tests/factories.py` (one per model,
sequenced names, no variant subclasses), and `tests/test_factories.py` asserting two builds
of each never collide.
Verified: `poetry run pytest tests/test_factories.py` — 2 failed, same
`OperationalError: no such table` (expected, pending T017). Lint clean.
Next: T016.
Watch: same — resolves at T017.

## 2026-09-21T23:00:41+02:00 · Implementer US-1 · T016

Did: added `document` and `draft` fixtures to `tests/conftest.py`, thin wrappers over
`DocumentFactory`/`VersionFactory`.
Verified: `poetry run pytest tests/ --collect-only -q` — 9 tests collected, no import
errors (conftest.py has no dedicated test of its own; later stories' modules are its
consumers). Lint clean.
Next: T017.
Watch: nothing.

## 2026-09-21T23:01:09+02:00 · Implementer US-1 · T017

Did: `poetry run python -m django makemigrations mvp_compliance` →
`mvp_compliance/migrations/0001_initial.py`.
Verified: `makemigrations --check --dry-run` — "No changes detected", exit 0. Migrating a
fresh sqlite database from empty reaches the same schema (`migrate` on a throwaway DB,
`mvp_compliance.0001_initial... OK`, file removed afterwards). Full suite:
`poetry run pytest tests/` — **9 passed**, including every test that was waiting on this
migration since T012.
Next: full verify (§5), then the completion report.
Watch: nothing.
