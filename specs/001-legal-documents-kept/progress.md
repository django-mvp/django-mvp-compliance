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

## 2026-09-22T00:30:00+02:00 · US-3 acceptance

Did: independent re-verification of US-3 rather than acceptance of its report.
Full suite 37 passed, `pre-commit run --all-files` green across all eight hooks
on a cleared lint cache, `makemigrations --check --dry-run` clean. The
guardrail scan flags `tests/test_models.py`; triaged as an import-block rewrite
with all eighteen pre-existing tests intact (D17).
Checked the declared deviation (D16) rather than taking it: removing
`use_in_migrations = True` leaves
`test_historical_version_model_uses_this_packages_manager` green, because
migration `0004` records the manager in state permanently. Added
`test_the_manager_is_declared_for_use_in_migrations`, confirmed red with the
attribute removed and green with it restored. D16 rewritten to say what the
tests cover. Suite now 38 passed.
Next: US-4.
Watch: nothing.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · T040

Did: `tests/test_rendering.py::TestMarkdownRenderer` — one test asserting
headings, emphasis, strong, lists, a link and a table survive rendering, and
that `<script>`, `<style>`, `<iframe>`, `onclick` and a `javascript:` link do
not, checking both presence and absence in the same output (FR-017).
Verified: `poetry run pytest tests/test_rendering.py -x` — collection error,
`ModuleNotFoundError: No module named 'mvp_compliance.rendering'` (RED for the
right reason: the module doesn't exist yet).
Next: T041.
Watch: `TestRendererSetting` (T043) lives in the same file and was written
alongside this test since the brief places both in `tests/test_rendering.py`
— see D18.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · T041

Did: added `markdown` and `nh3` to `[project] dependencies` in
`pyproject.toml`, each with a comment saying what it's for; `poetry lock`,
`poetry install --sync`.
Verified: `poetry lock` and `poetry install --sync` succeeded, installing
`markdown 3.10.3` and `nh3 0.3.7`. `deptry` not run in isolation at this
point — nothing imports either package yet, so it would fail by design (the
brief's own rationale for this task's placement); confirmed clean once T042
lands, see that entry.
Next: T042.
Watch: nothing.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · T042

Did: `mvp_compliance/rendering.py` — `MarkdownRenderer` with `extensions`,
`allowed_tags`, `allowed_attributes`, `allowed_url_schemes` class attributes
and `render()` running `markdown.markdown()` then `nh3.clean()`. Module
docstring states Article XIII.
Verified: manual script (T040's test file can't collect standalone until
T043's `get_renderer` also exists — D18) exercising every assertion in
`TestMarkdownRenderer` directly against `MarkdownRenderer().render()` — all
passed. First pass failed one assertion: `nh3` adds `rel="noopener
noreferrer"` to links by default, which isn't in plan.md's declared
`allowed_attributes` for `a`; fixed by passing `link_rel=None` to
`nh3.clean()` (D19). `poetry run ruff check`, `ruff format --check`, `mypy` —
all clean.
Next: T043.
Watch: nothing.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · T043

Did: `mvp_compliance/rendering.py` — `get_renderer()`, resolving
`MVP_COMPLIANCE_RENDERER` through `import_string`, defaulting to
`MarkdownRenderer`.
Verified: `poetry run pytest tests/test_rendering.py -v` — 3 passed
(`TestMarkdownRenderer` from T040 and both `TestRendererSetting` cases from
this task, now that the module collects). `deptry .` — clean, confirming
T041's dependency declarations are now used. `ruff check`, `ruff format
--check`, `mypy` — all clean.
Next: T044.
Watch: nothing.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · T044

Did: `mvp_compliance/models.py` — `Version.html` (`TextField(blank=True)`,
help_text, verbose_name); `publish()` renders `self.markdown` through
`get_renderer()` before the row lock is taken and stores it in `self.html`;
widened `version_status_agrees_with_published_at` to require `html=""` on a
draft and `html != ""` on a published version. `tests/test_models.py::TestPublishing`
gained four tests: rendering happens on publish, a draft's `html` is empty,
and both directions of the widened constraint refused by the database
directly via `bulk_create`.
Verified: `poetry run pytest tests/test_models.py::TestPublishing -v` — RED
first (`AttributeError`/`TypeError`, `html` didn't exist), then GREEN, 16
passed, after generating migration `0005` (needed for the new column to exist
in the test database — see D20 on why that migration's own commit waits for
T048). Two pre-existing tests in this class
(`test_status_and_published_at_must_agree`,
`test_a_published_version_must_have_a_publication_time`) were re-run
unmodified and stayed green — the widened constraint only adds restrictions,
it doesn't loosen the ones they exercise. `ruff check`, `ruff format
--check` (one file reformatted, applied), `mypy` — all clean.
Next: T045.
Watch: nothing.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · T045

Did: `publish()` now refuses with `PublishError` when the rendered output is
empty once stripped, checked immediately after rendering and before the
`transaction.atomic()` block — before the row lock and before anything is
written (FR-018, D7).
Verified: new test
`test_publishing_a_draft_whose_output_is_empty_once_stripped_is_refused` —
RED first (`IntegrityError` from the check constraint, since nothing refused
the publish before the write), then GREEN after the guard, along with the
rest of the class: `poetry run pytest tests/test_models.py -v` — 35 passed.
`ruff check`, `ruff format --check`, `mypy` — all clean.
Next: T046.
Watch: nothing.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · T046

Did: `test_stored_html_survives_a_renderer_change` — publishes, swaps
`MVP_COMPLIANCE_RENDERER` to a local `UppercaseRenderer` via
`override_settings`, re-reads, asserts the stored `html` is byte-identical to
what publication produced (US-4 scenario 3, SC-004).
Verified: passed on first run, as the brief's own acceptance expects ("no
model change implied by this task). Probed per `craft-tdd`'s mutation check
rather than trusting a first-run pass: temporarily made `save()` re-render
`html` in upper case on every write to a published row, re-ran the single
test, watched it fail with the expected mismatch, then reverted the
mutation with `git checkout -- mvp_compliance/models.py` and re-ran the full
suite green (36 passed) to confirm the revert was clean.
Next: T047.
Watch: nothing.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · T047

Did: `test_published_html_cannot_be_changed` — one test covering all three
write routes (`save()`, queryset `update()`, `bulk_update()`) refusing a
change to a published version's `html`; `PUBLISHED_FROZEN_FIELDS` gained
`"html"` between `"markdown"` and `"published_at"`, matching plan.md's
Immutability section. No other line changed — the four refusal routes read
the constant, per D-prior_decisions in the brief.
Verified: RED first (`Failed: DID NOT RAISE PublishedVersionError`), then
GREEN: `poetry run pytest tests/test_models.py -v` — 37 passed. `ruff
check`, `ruff format --check`, `mypy` — all clean.
Next: T048.
Watch: nothing.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · T048

Did: `poetry run python manage.py makemigrations mvp_compliance` — "No
changes detected" (migration `0005`, generated during T044 to make its tests
runnable, already covers every model change this story makes; T045 and T047
touched only Python-level behaviour and a module constant, neither needs a
schema change). Committed the migration file under this task, per the
brief's task split (D20).
Verified: `poetry run python manage.py makemigrations --check --dry-run` —
clean, exit 0. `deptry .` and `mypy mvp_compliance` — both clean across the
whole package.
Next: update `docs/models.md` (rendering and immutability sections described
the pre-US-4 state, including a line explicitly deferring rendering to "a
later story"), then the full verify (§5) and the completion report.
Watch: nothing.

## 2026-09-22T00:31:25+02:00 · Implementer US-4 · docs

Did: `docs/models.md` — added a Rendering section (`MarkdownRenderer`,
`get_renderer()`, the `MVP_COMPLIANCE_RENDERER` setting, the allow-list
behaviour), updated Publishing to mention `html` and the empty-output
refusal, updated Immutability's frozen-field list to include `html`, removed
the line stating rendering "is not here yet".
Verified: every code example on the page executed against this branch in a
throwaway script using a real test database (`DiscoverRunner.setup_databases`)
— `Document`/`Version` creation, `publish()`, `MarkdownRenderer().render()`,
and all five immutability-refusal routes each raised
`PublishedVersionError` as shown. All passed.
Next: full verify (§5).
Watch: nothing.

## 2026-09-22T00:45:00+02:00 · US-4 acceptance

Did: independent re-verification of US-4. Full suite 49 passed, all eight
pre-commit hooks green on a cleared lint cache, `makemigrations --check
--dry-run` clean, guardrail scan clean over c13c411..HEAD.
Checked D19 rather than taking it. Dropping `rel` from rendered links is safe
because `target` is not an allowed attribute, so a link cannot open a new
browsing context — but nothing asserted that, which left the argument one
allow-list widening away from being wrong silently. Added
`test_a_link_cannot_open_a_new_browsing_context`, confirmed red with `target`
allowed and green with it removed, and recorded what holds D19 up. Suite now
50 passed.
Next: US-5.
Watch: nothing.

## 2026-09-22T00:42:16+02:00 · Implementer US-5 · T050

Did: wrote `TestRetrieval` in `tests/test_models.py` — three tests covering
scenarios 1, 2 and 3 (published history in order with drafts absent, a
superseded version's original wording and stored HTML, the version in force
is the most recently published one).
Verified: `poetry run pytest tests/test_models.py::TestRetrieval -x` — failed
on the first test with `AttributeError: 'RelatedManager' object has no
attribute 'published'`, the right reason (the method does not exist yet).
Next: T051 — implement `published()`, `drafts()`, `current()` and
`Document.current`.
Watch: the manager-forwarding question named in the brief.

## 2026-09-22T00:42:16+02:00 · Implementer US-5 · T051

Did: `VersionQuerySet.published()`, `.drafts()`, `.current()`;
`VersionManager` forwards all three explicitly (D21 — `Manager.from_queryset()`
tried first, rejected by mypy); `Document.current` as a property returning
`self.versions.current().first()`.
Verified: `poetry run pytest tests/test_models.py::TestRetrieval` — 3 passed.
`poetry run mypy mvp_compliance` — Success: no issues found in 5 source
files. `poetry run ruff check mvp_compliance tests` and
`poetry run ruff format --check mvp_compliance tests` — both clean.
Next: T052 — the never-published case.
Watch: nothing.

## 2026-09-22T00:43:08+02:00 · Implementer US-5 · T052

Did: `test_a_document_with_nothing_published_reports_no_version_in_force` — a
freshly created document, then one with only a draft, both read
`document.current`.
Verified: `poetry run pytest tests/test_models.py::TestRetrieval` — 4 passed
on first run, T051's implementation already covers it (FR-008, SC-006).
Next: T053.
Watch: nothing.

## 2026-09-22T00:43:08+02:00 · Implementer US-5 · T053

Did: `test_one_version_by_its_number` — `document.versions.get(number=2)`
against a document with three versions.
Verified: `poetry run pytest tests/test_models.py::TestRetrieval` — 5 passed
on first run; the plain Django idiom needs no wrapper (FR-021).
Next: T054.
Watch: nothing.

## 2026-09-22T00:43:08+02:00 · Implementer US-5 · T054

Did: `test_four_documents_do_not_interfere` — four documents each
accumulating their own versions (one untouched, one draft-only, two
published to different depths), asserting numbering, `.current` and
`.published()` are exactly each document's own (SC-001).
Verified: `poetry run pytest tests/test_models.py::TestRetrieval` — 6
passed on first run. `poetry run ruff check tests` and
`poetry run ruff format --check tests` clean.
Next: T055 — README.
Watch: nothing.

## 2026-09-22T00:44:40+02:00 · Implementer US-5 · T055

Did: README — replaced the stale "scaffold only, no models" status banner
(unchanged since the initial scaffold, contradicted by every story since
US-1) with an accurate one, and added a "Models" section: what `Document`
and `Version` hold, publish/current/published() usage, the
`MVP_COMPLIANCE_RENDERER` setting, and what the package deliberately ships
none of (admin, forms, views, URLs). Also added a Retrieval section to
`docs/models.md` (D13's precedent: new public surface gets a page in the
story it belongs to) covering `document.current`, `.get(number=n)` and
`.published()`.
Verified: every code example in both pages run against this branch in a
throwaway script using a real test database (`DiscoverRunner.setup_databases`)
— document/version creation, `publish()`, `.current`, `.published()`,
`.drafts()`, `.get(number=...)`, `get_renderer()` all executed as shown.
`poetry run pre-commit run --files README.md docs/models.md` — trailing
whitespace, end-of-file and deptry checks passed.
Next: T056 — CHANGELOG.
Watch: nothing.

## 2026-09-22T00:44:40+02:00 · Implementer US-5 · T056

Did: CHANGELOG — replaced the stale "Initial scaffold, no models yet" prose
under `## [Unreleased]` (same staleness as the README banner T055 fixed)
with a Keep a Changelog `### Added` section naming `Document` and `Version`,
the two dependencies (`markdown`, `nh3`) and what each does, and the
`MVP_COMPLIANCE_RENDERER` setting.
Verified: `poetry run pre-commit run --files CHANGELOG.md` — trailing
whitespace, end-of-file and deptry checks passed.
Next: T057 — assert no admin/forms/views/urls.
Watch: nothing.

## 2026-09-22T00:45:32+02:00 · Implementer US-5 · T057

Did: `tests/test_app.py` — two new tests on `TestPackagedApp`:
`mvp_compliance.admin/forms/views/urls` don't exist as modules, and neither
`Document` nor `Version` is in `admin.site._registry` (D5).
Verified: `poetry run pytest tests/test_app.py` — 4 passed. Probed the new
absence-test rather than trusting it: added a throwaway
`mvp_compliance/admin.py`, confirmed the test failed with the expected
`AssertionError`, removed the file, confirmed green again.
`poetry run ruff check tests` clean; `ruff format` reformatted the file once
(parenthesised assert message), reran green. `poetry run mypy
mvp_compliance` — Success: no issues found in 5 source files.
Next: full verify (§5) — the story's last task.
Watch: nothing.
