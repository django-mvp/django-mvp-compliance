# Progress — 003 The record of who accepted which version

Run narrative. Newest entry last.

## 2026-09-22 — S3 PLAN

Picked off the feature queue as the only row reporting `ready`. The specification merged to main in
pull request #23 on 2026-09-21 at 21:22 UTC, and the issue graph was already built: epic #20,
stories #24 to #28.

FS-001 was delivered after this specification landed, so this specification was re-read against
FS-001's — a comparison of the two documents, not of this document against code. No contradiction:
FS-003 assumes a version that is published, in force or superseded, an at-most-one-in-force rule,
and a stored output fixed at publication, and FS-001 specifies exactly those. The spec's own closing
assumption, that FS-001 was specified and not yet delivered, is the only line that is now out of
date, and it changes nothing this feature builds.

Baseline verified green on `4f55e4d` before anything was written: lint, typecheck, test, build,
conformance and docs all pass.

Written this stage: `research.md`, `plan.md`, `tasks.md`, this file and `feature-state.json`.
`decisions.md` gained D7 to D11 — the five ambiguities the plan had to settle that the specification
did not reach.

The design in one line: one append-only model whose only write route is a manager method, the person
held twice so a record survives its account and still says whose it is, "at most one record per
person per version" as a unique constraint that `get_or_create()` rides, and the outstanding question
answered by one queryset that the single-document form narrows rather than restates.

## 2026-09-22 — S3R DESIGN REVIEW

One reviewer, three lenses, on sonnet. Verdict `approve`, risk low, one verified low finding and one
editorial note; receipts checked green both sides of the dispatch.

DR-001 is a good catch and its evidence was re-verified here against the Django the project actually
resolves. The `on_delete` callable delegating to `SET_NULL` works only because it is an ordinary
function: Django's own `SET_NULL` carries `lazy_sub_objs = True`, the collector reads that attribute
before calling the handler, and a handler that has it leaves `sub_objs` unevaluated, which sends the
field update through `QuerySet.update()` — where this package's guard refuses it. Adding the
attribute by analogy would break the default that says records survive. `research.md` R1, `plan.md`
and T052 all now say so, and US-4's T050 is the test that would notice.

No re-plan: nothing reached the critical or high bar that forces one.

## 2026-09-22T17:05:00+02:00 · Implementer US-1 · T001

Did: added `UserFactory` over `get_user_model()`, `factory.Sequence` on `username`, and
`TestUserFactory` asserting two builds don't collide.
Verified: `poetry run pytest tests/test_factories.py::TestUserFactory` — collection error,
`ImportError: cannot import name 'UserFactory'` (right reason). After adding the factory:
`poetry run pytest tests/test_factories.py` — 3 passed. `poetry run ruff check` clean.
Next: T002.
Watch: nothing.

## 2026-09-22T17:07:00+02:00 · Implementer US-1 · T002

Did: added a `user` fixture in `conftest.py`, wrapping `UserFactory`.
Verified: `poetry run pytest --fixtures tests/test_app.py` shows `user` registered.
`poetry run pytest tests/` — 66 passed (unchanged from T001 plus the new factory test; no
consumer of the fixture yet). `poetry run ruff check` clean.
Next: T010.
Watch: nothing.

## 2026-09-22T17:10:00+02:00 · Implementer US-1 · T010

Did: added `TestAcceptance` with the recording test, asserting the exact concrete field set
`{"id", "user", "subject", "version", "accepted_at", "ip_address"}`.
Verified: `poetry run pytest tests/test_models.py::TestAcceptance` — collection error,
`ImportError: cannot import name 'Acceptance'` (right reason: the model doesn't exist yet).
Next: T011.
Watch: nothing.

## 2026-09-22T17:12:00+02:00 · Implementer US-1 · T011

Did: added `test_no_way_to_accept_a_document` — no `document` field, no
`record_for_document` manager method, and `record(user, document)` raises `AttributeError`.
Verified: same scope, same `ImportError` (unchanged — right reason).
Next: T012.
Watch: nothing.

## 2026-09-22T17:14:00+02:00 · Implementer US-1 · T012

Did: added `TestRecording` — a draft is refused with `RecordError` and writes nothing; a
superseded version is accepted; a user with no primary key is refused the same way.
Verified: same scope, collection error now `ImportError: cannot import name 'RecordError'`
(right reason: neither `Acceptance` nor `RecordError` exist yet).
Next: T013.
Watch: nothing.

## 2026-09-22T17:17:00+02:00 · Implementer US-1 · T013

Did: built `Acceptance` — `user`, `subject`, `version`, `accepted_at`, `ip_address`, each
with a translated `verbose_name` and `help_text`; `subject`'s carries the Article XV
justification (D7); `Meta`, `__str__`, class docstring. No manager methods and no migration
yet.
Verified: `poetry run pytest tests/test_models.py::TestAcceptance tests/test_models.py::TestRecording`
— collection now fails on `ImportError: cannot import name 'RecordError' from
'mvp_compliance.exceptions'` rather than on `Acceptance` (model import now succeeds).
`poetry run ruff check mvp_compliance/models.py` and `poetry run mypy mvp_compliance/models.py`
both clean.
Next: T015 (moved ahead of T014 — see decisions.md D12).
Watch: T010–T012 stay red until `RecordError` (T015) and `record()` (T014) both land; this
is the correct order, not a defect.

## 2026-09-22T17:20:00+02:00 · Implementer US-1 · T015

Did: added `RecordError` and `RecordedAcceptanceError` to `exceptions.py`, each with a
docstring naming its requirement; extended `TestExceptions` with the matching
not-a-`ValidationError` and docstring assertions. Landed before T014 — D12.
Verified: `poetry run pytest tests/test_exceptions.py` — 8 passed. `poetry run ruff check`
and `poetry run mypy mvp_compliance/exceptions.py` both clean.
Next: T014.
Watch: nothing.

## 2026-09-22T17:24:00+02:00 · Implementer US-1 · T014

Did: added `Acceptance.subject_of(user)` (`staticmethod`, raises `RecordError` for a user
with no primary key) and `AcceptanceManager.record(user, version, request=None)` (refuses a
draft with `RecordError`, derives the subject, creates the row with
`accepted_at = timezone.now()`); `objects = AcceptanceManager()` on `Acceptance`.
Verified: `poetry run pytest tests/test_models.py::TestAcceptance tests/test_models.py::TestRecording`
— 1 passed (`test_no_way_to_accept_a_document`, no DB write on that path), 4 failed with
`OperationalError: no such table: mvp_compliance_acceptance`. Expected: no migration yet
(T021); the draft-refusal test's own `pytest.raises(RecordError)` passes before its trailing
`exists()` assertion hits the missing table. `poetry run ruff check mvp_compliance/models.py`
clean; `poetry run mypy mvp_compliance/models.py` needed `models.Manager["Acceptance"]`
(parameterized) instead of a bare `models.Manager`, then clean.
Next: T016.
Watch: T010, T012 stay red on the missing table until T021 lands the migration — correct
order, not a defect.

## 2026-09-22T17:30:00+02:00 · Implementer US-1 · T016

Did: added `TestAcceptanceImmutability` — one test per refused route: `save()` on an
existing row, `AcceptanceQuerySet.update()`, `bulk_update()`, `Acceptance.delete()`,
`AcceptanceQuerySet.delete()` (SC-001).
Verified: `poetry run pytest tests/test_models.py::TestAcceptanceImmutability` — all 5 fail
with `OperationalError: no such table: mvp_compliance_acceptance` (right reason: no
migration yet, T021). `poetry run ruff check tests/test_models.py` clean.
Next: T017.
Watch: nothing.

## 2026-09-22T17:35:00+02:00 · Implementer US-1 · T017

Did: added `AcceptanceQuerySet` (`update()` refuses whenever it matches anything,
`delete()` refuses outright); `AcceptanceManager.get_queryset()` returns it and
`use_in_migrations = True`; `Acceptance.save()` refuses when the row already exists in the
database (asked of the database, not Django's adding flag) and `Acceptance.delete()` refuses
outright.
Verified: `poetry run pytest tests/test_models.py::TestAcceptanceImmutability` — still 5
failed, all `OperationalError: no such table` (unchanged from T016 — the guard logic never
gets a chance to run before the missing table does; the migration is T021).
`poetry run ruff check mvp_compliance/models.py` and `poetry run mypy mvp_compliance/models.py`
both clean.
Next: T018.
Watch: nothing.

## 2026-09-22T17:40:00+02:00 · Implementer US-1 · T018

Did: added `test_a_historical_model_inherits_the_guard`, asserting a historical `Acceptance`
from migration state carries `AcceptanceManager`; broadened `test_migrations.py`'s module
docstring and its `RunPython`/`RunSQL` comment to name `Acceptance` alongside `Version` — the
assertion itself already covers every migration in the package generically and needed no
logic change.
Verified: `poetry run pytest tests/test_migrations.py tests/test_models.py::TestAcceptanceImmutability::test_a_historical_model_inherits_the_guard`
— the migrations test passes (1 passed), the historical-model test fails with
`LookupError: App 'mvp_compliance' doesn't have a 'Acceptance' model` (right reason: no
migration includes it yet, T021). `poetry run ruff check` clean (one import-ordering
auto-fix applied on `tests/test_models.py`).
Next: T019.
Watch: nothing.

## 2026-09-22T17:44:00+02:00 · Implementer US-1 · T019

Did: added `test_record_still_points_at_the_version_it_named` — an acceptance of a version
that is later superseded still points at that version afterwards (scenario 7, FR-007).
Verified: `poetry run pytest tests/test_models.py::TestAcceptance::test_record_still_points_at_the_version_it_named`
— fails with `OperationalError: no such table` (right reason, T021). `poetry run ruff check
tests/test_models.py` clean.
Next: T020.
Watch: nothing.

## 2026-09-22T17:48:00+02:00 · Implementer US-1 · T020

Did: added `AcceptanceFactory` (`SubFactory` on `user` and `version`, `subject` derived from
the user's pk, `accepted_at` supplied) and its test; `acceptance` fixture in `conftest.py`.
Verified: `poetry run pytest tests/test_factories.py::TestAcceptanceFactory` — fails with
`OperationalError: no such table` (right reason, T021). `poetry run ruff check` clean (two
import-ordering auto-fixes, on `tests/conftest.py` and `tests/test_factories.py`); `poetry
run mypy tests/factories.py` clean.
Next: T021.
Watch: nothing.

## 2026-09-22T17:52:00+02:00 · Implementer US-1 · T021

Did: `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
mvp_compliance` — generated `0002_acceptance.py` (depends on `0001_initial` and
`settings.AUTH_USER_MODEL`'s swappable dependency).
Verified: `--check --dry-run` reports no changes. Full narrow scope —
`poetry run pytest tests/test_models.py::TestAcceptance tests/test_models.py::TestRecording
tests/test_models.py::TestAcceptanceImmutability tests/test_migrations.py
tests/test_factories.py tests/test_exceptions.py` — 25 passed (every test that was red on
the missing table across T010–T020 is now green; pytest-django's in-memory database is
migrated from zero on every run, so this is also the migrate-from-zero proof). `poetry run
ruff check mvp_compliance/migrations/0002_acceptance.py` clean (one quoting auto-fix);
`poetry run mypy mvp_compliance/migrations/0002_acceptance.py` clean.
Next: T022.
Watch: nothing.

## 2026-09-22T17:58:00+02:00 · Implementer US-1 · T022

Did: added an `## Acceptance` section to `docs/models.md` (what the record is,
`Acceptance.objects.record()`, the draft refusal, the immutability routes in the style the
`Version` section uses); updated `README.md`'s status line and `## Models` section with
`Acceptance`.
Verified: every code example in both pages run against this branch — executed by hand
against a real test database (`Acceptance.objects.record()`, the draft refusal, and each of
the five immutability routes), all six behaved exactly as documented.
`poetry run pytest tests/ -q` — 83 passed (up from the 65 that were green at the story's
`verified_base`).
Next: US-1's own §5 verify, then the completion report.
Watch: nothing.

## 2026-09-22T18:10:00+02:00 · Implementer US-2 · T030

Did: three tests in `TestRecording` for scenarios 1, 2 and 4 — a later version leaves a
second record with the earlier one untouched; acceptances list in the order they
happened rather than the order of their rows (`timezone.now` patched via `monkeypatch`
so an earlier-timestamped acceptance is recorded after a later one, to prove the claim
isn't riding on insertion order); two people accepting the same version each get their
own record.
Verified: `poetry run pytest tests/test_models.py::TestRecording -v` — 6 passed, 1
failed (`test_acceptances_are_listed_in_the_order_they_happened`, right reason: no
`Meta.ordering` yet, so the query returns rows in insertion order). `poetry run ruff
check tests/test_models.py` clean; `poetry run mypy tests/test_models.py` clean.
Next: T031.
Watch: nothing.

## 2026-09-22T18:16:00+02:00 · Implementer US-2 · T031

Did: `TestRecording::test_the_same_version_twice_leaves_one_record` — scenario 3, D3.
Verified: fails — `record()` still calls `create()` unconditionally, so the repeat
writes a second row and `again == first` is false. `poetry run ruff check` and `mypy`
clean.
Next: T032.
Watch: nothing.

## 2026-09-22T18:22:00+02:00 · Implementer US-2 · T032

Did: `one_acceptance_per_person_per_version` unique constraint over `subject` and
`version` (comment on why `subject` rather than `user`); `Meta.ordering = ["accepted_at",
"id"]`; `record()` switched from `create()` to `get_or_create()` over that constraint.
Verified: `poetry run pytest tests/test_models.py::TestRecording -v` — 7 passed (T030
and T031 both green — `Meta.ordering` is query-time, not schema, so it took effect
without a migration). `poetry run pytest tests/test_models.py::TestAcceptance
tests/test_models.py::TestAcceptanceImmutability tests/test_migrations.py -q` — 10
passed, nothing else moved. `poetry run ruff check mvp_compliance/models.py` and `mypy`
clean.
Next: T033.
Watch: the unique constraint itself isn't in the applied schema yet — `makemigrations
--check` is dirty until T035.

## 2026-09-22T18:30:00+02:00 · Implementer US-2 · T033

Did: `TestRecording::test_a_second_row_is_refused_by_the_database` — forces a duplicate
past `record()` with `bulk_create()` and asserts `IntegrityError`, so FR-009 is shown to
be held by the constraint rather than by the method.
Verified: fails on this commit — `DID NOT RAISE IntegrityError` — for the reason noted
at T032: the constraint is on `Meta` but not yet in the applied schema. Same sequencing
T021 used for the table itself (T010–T020 stayed red on a missing table until the
migration landed). `poetry run ruff check` and `mypy` clean.
Next: T034.
Watch: nothing new.

## 2026-09-22T18:38:00+02:00 · Implementer US-2 · T034

Did: `TestRecording::test_two_recordings_leave_one_record` — scenario 5, FR-010, SC-003,
without threads or wall-clock timing. First attempt: monkeypatched `AcceptanceQuerySet.create`
to insert a competing row before calling through — wrong, because that insert landed
*inside* `get_or_create()`'s own `atomic()` block, so the `IntegrityError` rolled both
rows back together and the exception propagated instead of being recovered. Corrected to
monkeypatch `AcceptanceQuerySet.get` instead: the first (genuine) lookup misses, and only
as a side effect of that miss does it insert-and-commit the competing row as a sibling
`atomic()` block that releases *before* `get_or_create()`'s own `atomic()` opens — so when
`record()`'s own insert collides and its attempt is rolled back, the competing row
survives and the retried `get()` returns it.
Verified: fails on this commit for the same schema reason as T033. Probed per craft-tdd
before trusting it: reverted `record()` to the plain `create()` path — the test still
passed, because that path never calls `.get()` so the mock's side effect never fires
(expected: the test only speaks to the `get_or_create()`-based implementation). Reverted
`record()` instead to the hand-rolled `try: get() / except: create()` pattern
`research.md` R3 warns is unsafe — the test then failed with an uncaught `IntegrityError`,
confirming it does catch the exact regression the story exists to prevent. Both mutations
reverted with `git checkout`. `poetry run ruff check` and `mypy` clean. Squashed the
correction into this commit with `git commit --fixup` + `git rebase -i --autosquash`
rather than leaving a second commit for the same task, since T035 hadn't landed yet.
Next: T035.
Watch: nothing new.

