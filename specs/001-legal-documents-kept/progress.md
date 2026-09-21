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

## 2026-09-21T23:18:25+02:00 · Implementer US-2 · T020

Did: added `TestPublishing` to `tests/test_models.py` with the draft-state tests —
newly created is a draft with no publication time, freely editable, freely
discardable.
Verified: `poetry run pytest tests/test_models.py::TestPublishing` — 1 failed,
`AttributeError: 'Version' object has no attribute 'status'` (right reason: `status`
doesn't exist yet). Lint clean.
Next: T021.
Watch: nothing.

## 2026-09-21T23:18:25+02:00 · Implementer US-2 · T021

Did: added the publishing-scenario tests to `TestPublishing` — first draft published
makes it current with nothing superseded, a second publish supersedes the first and
leaves exactly one current, an already-published version refuses a second publish.
Verified: `poetry run pytest tests/test_models.py::TestPublishing` — collection error,
`ModuleNotFoundError: No module named 'mvp_compliance.exceptions'` (right reason:
`PublishError` doesn't exist yet, matching tasks.md's own "Fails before T023").
Next: T022.
Watch: nothing.

## 2026-09-21T23:18:25+02:00 · Implementer US-2 · T022

Did: added `Version.Status` (`draft`/`current`/`superseded`), the `status` field,
`published_at`, `is_published`, and the `version_status_agrees_with_published_at`
check constraint (D14 on why it matches `Status.DRAFT`'s literal value rather than
the enum). Added two tests of the constraint itself, forcing a draft with a
publication time and a published row with none via `bulk_create`. Migration
`0002_version_published_at_version_status_and_more`.
Verified: wrote the two constraint tests first — RED (`ModuleNotFoundError`, same
blocker as T021, since the whole module still fails to import without T023). Added
`mvp_compliance/exceptions.py` to the working tree only (not committed — that's
T023's) so the module could import and the new state/constraint work could be
verified in isolation: `poetry run pytest tests/test_models.py::TestPublishing -k
"draft or status_and or published_version_must"` — 7 passed. `poetry run
manage.py makemigrations mvp_compliance --check` — clean after generating 0002.
`poetry run pre-commit run --files mvp_compliance/models.py
mvp_compliance/migrations/0002_....py` — clean (ruff format caught the
`CheckConstraint.check` deprecation in favor of `.condition`, fixed and
regenerated the migration).
Next: T023.
Watch: `exceptions.py` exists in the working tree ahead of its own task; only
`models.py`, the migration and the two new tests were staged for this commit.

## 2026-09-21T23:18:25+02:00 · Implementer US-2 · T023

Did: `mvp_compliance/exceptions.py` — `PublishError`, `PublishedVersionError`, each
docstring naming its requirement, neither subclassing `ValidationError` (D9).
`tests/test_exceptions.py` asserts both.
Verified: `poetry run pytest tests/test_exceptions.py` — 4 passed. Lint clean.
Next: T024.
Watch: nothing.

## 2026-09-21T23:18:25+02:00 · Implementer US-2 · T024

Did: `Version.publish()` — refuses with `PublishError` when not a draft, then inside
`transaction.atomic()` locks the document with `select_for_update()`, supersedes the
current version, and saves this one as current with `published_at` set. Comment at
the lock names why it isn't belt-and-braces (research.md R1, D11).
Verified: `poetry run pytest tests/test_models.py::TestPublishing
tests/test_exceptions.py` — 12 passed, including T021's three tests turning green.
`poetry run pre-commit run --files mvp_compliance/models.py` — ruff format reflowed
one line; re-ran tests after, still 12 passed.
Next: T025.
Watch: nothing.

## 2026-09-21T23:18:25+02:00 · Implementer US-2 · T025

Did: added the `one_current_version_per_document` partial unique constraint and
`test_second_current_row_is_refused_by_the_database`, which bypasses `publish()`
entirely — a raw `queryset.update()` forcing a second current row — to prove the
database, not the method, is what refuses it. Migration
`0003_version_one_current_version_per_document`.
Verified: test written first — RED, `Failed: DID NOT RAISE IntegrityError` (right
reason: constraint didn't exist yet). Added the constraint, regenerated the
migration — `poetry run pytest tests/test_models.py::TestPublishing` — 9 passed.
Lint clean.
Next: T026.
Watch: nothing.

## 2026-09-21T23:18:25+02:00 · Implementer US-2 · T026

Did: added `test_two_publishes_leave_one_version_in_force` — asserts the invariant
holds immediately after each of two sequential publishes against the same document,
no wall-clock timing or thread scheduling involved.
Verified: `poetry run pytest
tests/test_models.py::TestPublishing::test_two_publishes_leave_one_version_in_force`
— 1 passed (regression check against T024/T025's already-built behaviour, not new
capability). Lint clean.
Next: T027.
Watch: nothing.

## 2026-09-21T23:18:25+02:00 · Implementer US-2 · T027

Did: added `test_no_reverse_operation_exists` — asserts by name that neither
`Version` nor `Version.objects` carries `unpublish`, `revert`, `rollback`,
`make_current` or `restore`. Nothing implemented; this is FR-009 held by absence.
Verified: `poetry run pytest
tests/test_models.py::TestPublishing::test_no_reverse_operation_exists` — 1 passed.
Lint clean.
Next: T028.
Watch: nothing.

## 2026-09-21T23:18:25+02:00 · Implementer US-2 · T028

Did: verified the migration state this story left, rather than generating a new
migration — 0002 and 0003 were already written as part of T022 and T025 per
`craft-increments`' rule that migrations are part of the slice that changes the
model, not a separate cleanup pass.
Verified: `poetry run python manage.py makemigrations mvp_compliance --check
--dry-run` — "No changes detected", exit 0. Migrated a fresh sqlite file from empty
on a throwaway settings module pointed at it — `0001_initial`, `0002_...`,
`0003_...` all applied `OK`, exit 0, file removed afterwards.
Next: docs/models.md, then the full verify (§5) and the completion report.
Watch: nothing.

## 2026-09-21T23:34:03+02:00 · Implementer US-3 · T030

Did: wrote `TestImmutability` in `tests/test_models.py` — one test per mutation
route per SC-003 (`save()`, `.update()`, `.bulk_update()`, instance `.delete()`,
queryset `.delete()`), each asserting `PublishedVersionError` and that the stored
wording is unchanged afterwards. Added a `published_version` fixture to
`conftest.py`.
Verified: `poetry run pytest tests/test_models.py::TestImmutability` — 5 failed,
all `DID NOT RAISE PublishedVersionError` (the right reason: no guard exists
yet). Lint clean.
Next: T031.
Watch: nothing.

## 2026-09-21T23:34:03+02:00 · Implementer US-3 · T031

Did: `PUBLISHED_FROZEN_FIELDS`, `VersionQuerySet.update()`/`.delete()`,
`Version.delete()` and a `save()` guard (`_refuse_if_published_wording_changed`)
that re-reads the stored row rather than trusting the in-memory instance. No
`bulk_update()` override (ARC-001). The frozen-field comparison uses each
field's `name` and `attname`. Also added an explicit test that a status-only
update on a published version still passes (FR-013).
Deviated: `models.Manager.from_queryset(VersionQuerySet)` failed mypy
("Unsupported dynamic base class"); replaced with `VersionManager(models.Manager)`
overriding `get_queryset()` to return `VersionQuerySet(self.model, using=self._db)`
— behaviourally identical since `VersionQuerySet` only overrides existing
`QuerySet` methods, not new ones, so the base `Manager`'s already-generated
wrappers (`update`, `delete`, `bulk_update`, `filter`, ...) all resolve through
it. `Version._meta.get_field(name).attname` needed `typing.cast(models.Field, ...)`
to satisfy mypy's `Field | ForeignObjectRel` return type (an `assert isinstance`
tripped ruff's S101).
Verified: `poetry run pytest tests/test_models.py` — 22 passed (the 5 from T030,
now green, plus the new status-only test, plus every pre-existing test in the
file still green). `poetry run pre-commit run --files mvp_compliance/models.py
mvp_compliance/migrations/0004_alter_version_managers.py` — all hooks passed,
including mypy and ruff. `makemigrations --check --dry-run` required a new
migration for the manager change (`AlterModelManagers`, not a data migration) —
generated as `0004_alter_version_managers.py`.
Next: T032.
Watch: nothing.

## 2026-09-21T23:34:03+02:00 · Implementer US-3 · T032

Did: `test_historical_version_model_uses_this_packages_manager` — loads the
migration graph's project state at `mvp_compliance`'s leaf migration via
`MigrationLoader` and confirms the historical model's `objects` is an instance
of `VersionManager`.
Deviated (D16): `use_in_migrations = True` was already written in T031's commit
alongside the rest of `VersionManager`, so this test is green from the moment
it exists rather than failing first — recorded in `decisions.md` rather than
manufacturing a red state that was not real.
Verified: `poetry run pytest
tests/test_models.py::TestImmutability::test_historical_version_model_uses_this_packages_manager`
— 1 passed. Lint clean.
Next: T033.
Watch: nothing.

## 2026-09-21T23:34:03+02:00 · Implementer US-3 · T033

Did: new `tests/test_migrations.py` (declared in `non-mirror-paths` already) —
reads every operation in every migration module under
`mvp_compliance/migrations/` and fails on a `RunPython` or `RunSQL` (D10). A
comment says what a legitimate future data migration must do instead.
Verified: `poetry run pytest tests/test_migrations.py` — 1 passed. Sanity-checked
the assertion actually fires, without touching a real migration file, by
constructing a bare `RunPython`/`RunSQL` instance in a throwaway interpreter and
confirming `isinstance(..., (RunPython, RunSQL))` is `True` for both. Lint clean.
Next: T034.
Watch: nothing.

## 2026-09-21T23:34:03+02:00 · Implementer US-3 · T034

Did: `test_superseding_does_not_change_the_wording` — a version superseded by a
later publish keeps its original `markdown` (FR-013, scenario 3).
Verified: `poetry run pytest
tests/test_models.py::TestImmutability::test_superseding_does_not_change_the_wording`
— 1 passed (green immediately: T031's guard and `publish()`'s status-only
`.update()` already give this). Lint clean.
Next: T035.
Watch: nothing.

## 2026-09-21T23:34:03+02:00 · Implementer US-3 · T035

Did: three tests — deleting a document holding a version raises
`ProtectedError` and leaves the document in place; a document holding none
deletes normally; discarding a document's only draft returns it to that empty
state and it then deletes normally too (FR-014, D8, edge case 4).
Verified: `poetry run pytest tests/test_models.py::TestImmutability -k document`
— 3 passed (green immediately: `on_delete=PROTECT` already closes this route,
per D8 — no `Document.delete()` override written). Lint clean.
Next: T036.
Watch: nothing.

## 2026-09-21T23:34:03+02:00 · Implementer US-3 · T036

Did: `test_correcting_an_error_makes_a_new_version` — publishes an erroneous
version, then a correcting one; the erroneous version stays readable with its
original wording and superseded standing (SC-007, scenario 6).
Verified: `poetry run pytest
tests/test_models.py::TestImmutability::test_correcting_an_error_makes_a_new_version`
— 1 passed. Lint clean.
Next: docs/models.md, then the full verify (§5) and the completion report.
Watch: nothing.
