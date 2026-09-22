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

## 2026-09-22T18:50:00+02:00 · Implementer US-2 · T035

Did: `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
mvp_compliance` — generated `0003_alter_acceptance_options_and_more.py` (the `Meta`
options change and the `AddConstraint`).
Verified: `--check --dry-run` reports no changes. `poetry run pytest
tests/test_models.py::TestAcceptance tests/test_models.py::TestRecording
tests/test_models.py::TestAcceptanceImmutability tests/test_migrations.py
tests/test_factories.py tests/test_exceptions.py -q` — 31 passed, including T033 and
T034 which were red since their own commits. `poetry run ruff check
mvp_compliance/migrations/0003_alter_acceptance_options_and_more.py` and `mypy` clean.
Next: T036.
Watch: nothing.

## 2026-09-22T18:56:00+02:00 · Implementer US-2 · T036

Did: added the later-version and repeat behaviour to `docs/models.md`'s `Acceptance`
section — stated as what happens, not as an API note — plus that acceptances come back
in the order they happened.
Verified: both code examples executed by hand against a real test database (a scratch
pytest module exercising the exact lines, removed afterwards) — both behaved exactly as
documented. `poetry run ruff check .` clean.
Next: US-2's own §5 verify, then the completion report.
Watch: nothing.

## 2026-09-22T19:40:00+02:00 · Orchestrator · US-2 accepted

Did: picked the story up at acceptance after the completion never registered — every task was
committed through T036 and the report written, but the ledger still read the story as open. Ran the
craft-skill receipt gate against the report and the brief it was dispatched with (both receipts
matched), then re-verified independently rather than reading the report back: 89 tests pass with
randomisation and parallelism off, lint after clearing the cache, types, dependency check, build and
structure checks all green, and `makemigrations --check` clean across every app rather than just
this one. Probed T034's race test against the defect it exists to catch, by reinstating the
hand-rolled get/except/create pattern in `record()` — the test failed with the uncaught
`IntegrityError`, so the test is load-bearing and not passing by construction. The guardrail flags
one file for the US-2 range alone, `tests/test_models.py`, and the only line it removed is an import
replaced by a wider one, so D13 covers it unchanged. Took the report's SC-002 concern as a real gap
and closed it rather than recording it (D15).
Verified: `forge verify` green end to end; `poetry run pytest tests/ -q` — 89 passed.
Next: US-3.
Watch: nothing. Everything from US-1's first task onward is still local — the branch on the remote
is the S3 artifact commit, so the checks showing green on the pull request predate all of it.

## 2026-09-22T19:45:00+02:00 · Implementer US-3 · T040

Did: added `TestOutstanding` to `tests/test_models.py` with the four single-document
scenarios (1, 2, 3, 5) — accepted-the-version-in-force, never-accepted, accepted-a-
superseded-version, and nothing-ever-published — each calling `document.is_outstanding_for(user)`.
Verified: `poetry run pytest tests/test_models.py::TestOutstanding -v` — all four fail
with `AttributeError: 'Document' object has no attribute 'is_outstanding_for'`, the
right reason (the method doesn't exist yet).
Next: T041.
Watch: nothing.

## 2026-09-22T19:50:00+02:00 · Implementer US-3 · T041

Did: added the multi-document scenarios (4, 6) to `TestOutstanding` —
`test_outstanding_for_names_exactly_the_unaccepted_documents` builds one accepted, one
superseded-then-reaccepted-required, one never-accepted and one never-published
document and asserts `Document.objects.outstanding_for(user)` names exactly the
superseded and never-accepted ones; `test_nothing_outstanding_is_an_empty_result_not_an_error`
asserts an empty queryset rather than an exception.
Verified: `poetry run pytest tests/test_models.py::TestOutstanding -v` — both new tests
fail with `AttributeError: 'Manager' object has no attribute 'outstanding_for'`.
Next: T042.
Watch: nothing.

## 2026-09-22T19:58:00+02:00 · Implementer US-3 · T042

Did: `mvp_compliance/models.py` gained `DocumentQuerySet.outstanding_for(user)` — one
query with a subquery per `research.md` R4 (`filter(versions__status=CURRENT).exclude(
pk__in=accepted.values("version__document_id"))`), `DocumentManager` forwarding it in
the same shape as `VersionManager`, `Document.objects = DocumentManager()`, and
`Document.is_outstanding_for(user)` as that same queryset narrowed to `self.pk` (D11) —
not a second expression of the rule.
Verified: `poetry run pytest tests/test_models.py::TestOutstanding -v` — 6 passed (T040's
four plus T041's two). `poetry run pytest tests/test_models.py -q` — 72 passed, no
regressions. `poetry run ruff check mvp_compliance/models.py tests/test_models.py` and
`poetry run mypy mvp_compliance/models.py` clean. `makemigrations --check --dry-run` —
no changes detected, as expected: no field or model shape changed.
Next: T043.
Watch: nothing.

## 2026-09-22T20:05:00+02:00 · Implementer US-3 · T043

Did: added `test_the_answer_costs_a_fixed_number_of_queries` — measures
`Document.objects.outstanding_for(user)` with `django_assert_num_queries(1)` at two
published documents and again at ten, and asserts the two captured-query counts are
equal.
Verified: passed immediately, since T042's mechanism was already the single-query
shape — nothing to observe red about it as new behaviour. Per craft-tdd's rule that an
already-covered criterion must be probed rather than trusted, mutated
`outstanding_for` to a per-document loop (one `.exists()` query per candidate document
plus a final re-fetch) and re-ran the test: failed with "Expected to perform 1 queries
but 4 were done" against 2 documents, confirming the assertion is load-bearing and
would catch an N+1 regression. Reverted the mutation with `git checkout --
mvp_compliance/models.py`, leaving only the new test. `poetry run pytest
tests/test_models.py::TestOutstanding -v` — 7 passed. `poetry run ruff check
tests/test_models.py` clean.
Next: T044.
Watch: nothing.

## 2026-09-22T20:10:00+02:00 · Implementer US-3 · T044

Did: added an *Outstanding* subsection to `docs/models.md` under `Acceptance`, naming
both entry points (`document.is_outstanding_for(user)` and
`Document.objects.outstanding_for(user)`), stating that a document with no published
version is never outstanding for anybody, and stating that the answer is deliberately
unfiltered by whether a site enforces a document.
Verified: both code examples executed by hand against a real test database (a scratch
pytest module exercising the exact lines, removed afterwards) — both behaved exactly as
documented. `poetry run ruff check .` clean.
Next: US-3's own §5 verify, then the completion report.
Watch: nothing.

## 2026-09-22T20:20:00+02:00 · Orchestrator · US-3 accepted

Did: ran the craft-skill receipt gate against the report and the brief the story was dispatched with
(both matched), then re-verified rather than reading the report back. 96 tests pass with
randomisation and parallelism off, `makemigrations --check` is clean across every app, and the
guardrail is clean for this story's range — no pre-existing test was touched. Probed T043's query
bound independently of the Implementer's own probe: replaced `outstanding_for()` with a loop that
asks each document separately, and the test failed with six queries where it expects one, so the
bound is load-bearing against the regression it exists to catch. Fixed a formatting-only miss in
`tests/test_models.py` that the story's commits left behind — a test signature that fits on one line
at 88 characters — which the code quality check would have failed on.
Verified: `forge verify` green end to end after the fix; `pre-commit run --all-files` green on a
cleared cache; `poetry run pytest tests/ -q` — 96 passed.
Next: US-4.
Watch: the branch still conflicts with main, which moved when FS-002 merged at 15:55. Until that is
resolved the pull request runs no checks at all, because the merge ref cannot be built — it reads as
quiet rather than failing. Integrate before the review gate.

## 2026-09-22T20:55:00+02:00 · Orchestrator · integrated main

Did: merged `origin/main` into the branch now rather than at convergence, because the pull request
had stopped running checks entirely — the authoring and publishing feature merged at 15:55, the two
branches conflicted in five files, and a conflicted pull request gives GitHub no merge commit to
build. Resolved all five: kept main's richer `UserFactory` and dropped this branch's, renumbered
this branch's two migrations to `0003` and `0004` behind main's `0002` so the app has one leaf again,
regenerated the message catalogue (main added a test that every shipped string is in it), and
rewrote the README's status and models sections to describe both features rather than either one.
Fixed the fuzzy catalogue entry that had been given another message's text. D16 records the lot.
Verified: 186 tests pass with randomisation and parallelism off, `pre-commit run --all-files` green
on a cleared cache, `makemigrations --check` clean across every app, and `migrate --plan` from zero
reaches the constraint through a single chain.
Next: US-4.
Watch: T070's squash target moved to `0003_*`, and T001's recorded evidence names a test that the
merge renamed.

## 2026-09-22T18:29:00+02:00 · Implementer US-4 · T050

Did: added `TestAccountRemoval::test_acceptances_survive_by_default` to
`tests/test_models.py` — records an acceptance, deletes the account, and asserts the
acceptance still exists with its `subject` and `version` unchanged and `user_id` cleared
(scenarios 1, 2, SC-006).
Verified: passed on first run, because the field's current placeholder is a plain
`on_delete=models.SET_NULL` that happens to match the default setting's target
behaviour — nothing wrong yet for it to be red about. Per craft-tdd's rule to probe
rather than trust an assertion that passes without new production code, mutated the
field to `on_delete=models.CASCADE` and reran: failed with `Acceptance.DoesNotExist`,
confirming the assertion is load-bearing and would catch the record actually being
removed. Reverted the mutation with `git checkout -- mvp_compliance/models.py`, leaving
only the new test. `poetry run pytest tests/test_models.py::TestAccountRemoval -v` — 1
passed. `poetry run ruff check tests/test_models.py` clean.
Next: T051.
Watch: nothing.

## 2026-09-22T18:34:00+02:00 · Implementer US-4 · T051

Did: added three tests to `TestAccountRemoval` — `test_acceptances_removed_when_the_setting_says_so`
(scenario 4, SC-007: with the setting off, removing the account leaves none of that
person's acceptances) and two isolation tests, one per setting, asserting a survivor's
acceptance is untouched when a different account is removed (scenario 5, FR-015).
Verified: `test_acceptances_removed_when_the_setting_says_so` failed red for the right
reason — `AssertionError: assert not True`, because the field is still the hardcoded
`on_delete=models.SET_NULL` placeholder and ignores the setting entirely. The two
isolation tests passed on first run: cross-account isolation on a `ForeignKey` delete is
scoped by Django's own collector to the rows referencing the deleted instance,
independent of which branch (`SET_NULL`/`CASCADE`) is chosen, so there is no wrong
production behaviour available to reproduce red against before T052 exists — probing
would exercise Django's collector rather than anything this story writes. Kept both:
they are the regression tests that would catch T052's callable breaking that scoping
(for example by issuing an unscoped delete or update). `poetry run pytest
tests/test_models.py::TestAccountRemoval -v` — 1 failed (as expected), 3 passed.
`poetry run ruff check tests/test_models.py` clean.
Next: T052.
Watch: nothing.

## 2026-09-22T18:41:00+02:00 · Implementer US-4 · T052

Did: added `acceptances_survive_account_removal()` and the `on_delete` callable
`keep_or_remove_acceptances(collector, field, sub_objs, using)` to
`mvp_compliance/models.py` (research.md R1, D8) — it reads the setting per delete and
delegates to Django's own `SET_NULL` or `CASCADE`. Switched `Acceptance.user.on_delete`
to it. The callable's docstring covers the three things T052 requires: the setting is
read per delete rather than per process, which is what makes it a setting; the field
stays `null=True` because `ForeignKey._check_on_delete` compares `on_delete == SET_NULL`
by identity and will not flag a delegating callable; and the callable must never be
given a `lazy_sub_objs` attribute, because that would route the field update through
`AcceptanceQuerySet.update()`'s refusal instead of the raw update the collector would
otherwise issue (research.md R1).

Generated the migration (`0005_alter_acceptance_user.py`) in this same commit rather
than waiting for T056, because craft-increments requires the tree to stay green between
slices "including migrations" and this field change alone makes `makemigrations --check`
dirty — deferring it to T056 would mean committing a slice with a known-dirty migration
state. Noted as a deviation from tasks.md's literal per-task split; T056 still runs and
records its own evidence, confirming the migration this task already generated is
sufficient and nothing further is pending.

Verified: `poetry run pytest tests/test_models.py::TestAccountRemoval -v` — 4 passed
(T050 and T051 both green). `poetry run pytest tests/ -q` — 190 passed, no regressions.
`poetry run ruff check mvp_compliance/models.py mvp_compliance/migrations/0005_alter_acceptance_user.py
tests/test_models.py` clean. `poetry run mypy mvp_compliance/models.py` clean.
`DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check --dry-run`
— "No changes detected".
Next: T053.
Watch: nothing.

## 2026-09-22T18:44:00+02:00 · Implementer US-4 · T053

Did: added `test_a_surviving_record_is_still_found_with_its_siblings` to
`TestAccountRemoval` — records two acceptances at distinct, controlled moments
(`monkeypatch` on `timezone.now`, the same technique `TestRecording` already uses for
ordering), removes the account, and asserts `Acceptance.objects.for_subject(subject)`
returns both together and in the order they happened (scenario 3, FR-014).
Verified: failed red for the right reason — `AttributeError: 'AcceptanceManager' object
has no attribute 'for_subject'`, since neither the queryset method nor the manager
forward exists yet. `poetry run ruff check tests/test_models.py` clean.
Next: T054.
Watch: nothing.

## 2026-09-22T18:47:00+02:00 · Implementer US-4 · T054

Did: added `AcceptanceQuerySet.for_subject(subject)` (filters on the stored identifier)
and `AcceptanceManager.for_subject` / `for_person(user)` to `mvp_compliance/models.py`.
`for_person()` is a thin call through `Acceptance.subject_of(user)` into
`for_subject()`, not a second query.
Verified: `poetry run pytest tests/test_models.py::TestAccountRemoval -v` — 5 passed
(T053 now green). `poetry run pytest tests/test_models.py -q` — 84 passed, no
regressions. `poetry run ruff check mvp_compliance/models.py tests/test_models.py` and
`poetry run mypy mvp_compliance/models.py` clean.
`DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check --dry-run`
— "No changes detected" (no field changed, as expected).
Next: T055.
Watch: nothing.

## 2026-09-22T18:50:00+02:00 · Implementer US-4 · T055

Did: added `test_a_recreated_account_inherits_nothing` to `TestAccountRemoval` — removes
an account, creates a new one with the same username, and asserts
`Acceptance.objects.for_person(recreated)` is empty (the spec's own edge case; what
holding `subject` as the primary key buys).
Verified: passed on first run, as tasks.md's own criterion for this task expects
("Passes", not "Fails before"), since T054's machinery already gives the right answer by
construction. Probed anyway per craft-tdd: temporarily changed `Acceptance.subject_of`
to derive the identifier from `user.username` instead of `user.pk` and reran — failed,
returning the original account's acceptance to the recreated one, confirming the
assertion is load-bearing against exactly the regression the edge case exists to catch.
Reverted with `git checkout -- mvp_compliance/models.py`. `poetry run pytest
tests/test_models.py::TestAccountRemoval -v` — 6 passed. `poetry run ruff check
tests/test_models.py` clean.
Next: T056.
Watch: nothing.

## 2026-09-22T18:53:00+02:00 · Implementer US-4 · T056

Did: nothing to generate — the one schema change this story makes (`Acceptance.user`'s
`on_delete`) was already migrated in T052's commit (`0005_alter_acceptance_user.py`),
because craft-increments requires the tree to stay green, migrations included, between
every slice, and deferring it to this task would have left T052 through T055 sitting on
a dirty migration state. This task verifies that decision was sufficient.
Verified: `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django
makemigrations mvp_compliance` — "No changes detected in app 'mvp_compliance'".
`DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
--check --dry-run` — "No changes detected", exit 0. `DJANGO_SETTINGS_MODULE=tests.settings
poetry run python -m django migrate --plan` — one chain from zero through
`mvp_compliance.0005_alter_acceptance_user`, main's `0001` and `0002` and this branch's
`0003` and `0004` all present and in order ahead of it.
Next: T057.
Watch: nothing.

## 2026-09-22T18:58:00+02:00 · Implementer US-4 · T057

Did: added an *Account removal* subsection to `docs/models.md` under `Acceptance`,
naming `MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL`, its default (`True`),
`for_person()`/`for_subject()` as how to find a person's records once the account is
gone, the recreated-account edge case, and the default's cost stated plainly: closing
an account does not remove what this package holds about that person (D1). Extended
the README's `Acceptance` paragraph with the setting, its default, and
`for_subject()`, and pointed to `docs/models.md` for the rest.
Verified: both documented code paths executed against a real test database — a scratch
pytest module (`tests/test_docs_scratch.py`) covering the default-survival example, the
setting-off example, and the `for_person()` example, all as documented; passed, removed
afterwards. Diffed `mvp_compliance/models.py` against this story's base commit
(`2677d20`) and confirmed no new `gettext_lazy` string was introduced anywhere in the
story, so the message catalogue needs no regeneration. `poetry run pytest tests/ -q` —
192 passed (186 at the base plus this story's 6). `poetry run ruff check .` and
`poetry run mypy mvp_compliance/models.py` clean.
Next: this story's own completion report.
Watch: nothing.

## 2026-09-22T21:40:00+02:00 · Orchestrator · US-4 accepted

Did: receipts matched the brief, 192 tests green, migrations clean across every app. Probed the two
claims this story turns on rather than reading them back. The setting is genuinely read per delete —
two removals in one process under opposite `override_settings` blocks each follow the live value.
The second claim did not hold: research R1 and the callable's docstring both said that adding
`lazy_sub_objs` would route the update into the queryset's refusal and break account removal under
the default, and it does not. The collector builds `sub_objs` from `Acceptance._base_manager`, which
is a plain manager, so there is no `update()` override in that path to hit. The refusal needs the
attribute *and* `base_manager_name` naming `AcceptanceManager`; either alone is inert, measured all
four ways. Corrected research.md, plan.md, tasks.md T052 and the docstring, and added a test pinning
both halves, checked against the defect — reintroducing the attribute fails it.
Verified: 193 tests pass with randomisation and parallelism off, `pre-commit run --all-files` green
on a cleared cache, `makemigrations --check` clean across every app.
Next: US-5.
Watch: nothing new.

## 2026-09-22T18:48:00+02:00 · Implementer US-5 · T060

Did: added `TestOptionalEvidence` to `tests/test_models.py` with the two tests scenarios 1
and 2 need — the package's defaults hold no address at all, and turning
`MVP_COMPLIANCE_RECORD_IP_ADDRESS` on with a request supplied holds it alongside the three
facts.
Verified: `poetry run pytest tests/test_models.py::TestOptionalEvidence -v` — the
setting-on test failed for the right reason (`assert None == '203.0.113.5'`, `record()`
never reads `request`). The defaults test passed on first run because `ip_address` is
already `None` by construction and nothing writes it yet, so per craft-tdd it needed
probing rather than trusting: temporarily added a literal `"ip_address": "9.9.9.9"` to
`record()`'s `defaults` and reran — failed (`assert '9.9.9.9' is None`), confirming the
assertion is load-bearing. Reverted with `git checkout -- mvp_compliance/models.py` before
committing. `poetry run ruff check tests/test_models.py` clean.
Next: T061.
Watch: nothing.

## 2026-09-22T18:52:00+02:00 · Implementer US-5 · T061

Did: added the two `TestOptionalEvidence` tests scenarios 3 and 4 need — a record made
before `MVP_COMPLIANCE_RECORD_IP_ADDRESS` was turned on stays unchanged once it is, and
a record made while it was on still holds the address once it is turned off again.
Verified: `poetry run pytest tests/test_models.py::TestOptionalEvidence -v` — the
turned-off-again test failed for the right reason (`assert None == '203.0.113.5'`,
`record()` still never reads `request`). The turned-on-later test passed on first run for
the same reason T060's default test did — `ip_address` is already `None` by construction.
Probed it the same way: temporarily added a literal `"ip_address": "9.9.9.9"` to
`record()`'s `defaults` and reran — failed (`assert '9.9.9.9' is None`), confirming the
assertion is load-bearing. Reverted with `git checkout -- mvp_compliance/models.py` before
committing. `poetry run ruff check tests/test_models.py` clean.
Next: T062.
Watch: nothing.

## 2026-09-22T18:56:00+02:00 · Implementer US-5 · T062

Did: `record()` now reads `request.META.get("REMOTE_ADDR")` into `ip_address` when
`MVP_COMPLIANCE_RECORD_IP_ADDRESS` is on and a request was supplied, and leaves it `None`
otherwise. The address is only ever placed in `get_or_create()`'s `defaults`, so it applies
solely to a record being newly created — a repeat call against an existing record returns
it untouched, which is what keeps T061's two scenarios true without any code written for
them specifically. The comment above the read states plainly that only `REMOTE_ADDR` is
read and `X-Forwarded-For` and every other forwarded header are refused, and why (a
forwarded header is client-set, so reading one hands the evidence field to the person it
is evidence about; research.md R6, D10).
Verified: `poetry run pytest tests/test_models.py::TestOptionalEvidence -v` — 4 passed.
`poetry run pytest tests/test_models.py::TestRecording tests/test_models.py::TestAccountRemoval
tests/test_models.py::TestAcceptanceImmutability -v` — 22 passed, confirming the shared
`record()` path is unaffected. `poetry run ruff check mvp_compliance/models.py
tests/test_models.py` and `poetry run mypy mvp_compliance/models.py` clean.
Next: T063.
Watch: nothing.

## 2026-09-22T18:59:00+02:00 · Implementer US-5 · T063

Did: added `TestOptionalEvidence::test_no_request_holds_no_address` — with the setting on
and no request supplied, recording succeeds and `ip_address` stays empty, so a management
command or a shell session needs no invented value.
Verified: `poetry run pytest tests/test_models.py::TestOptionalEvidence::test_no_request_holds_no_address -v`
passed on first run, matching tasks.md's own criterion for this task ("Passes", not "Fails
before") — T062's `request is not None` guard already gives the right answer by
construction. Probed anyway per craft-tdd: temporarily dropped that guard so the setting
alone triggered the `request.META` read, and reran — failed with
`AttributeError: 'NoneType' object has no attribute 'META'`, the exact regression the test
exists to catch. Reverted with `git checkout -- mvp_compliance/models.py` before
committing. `poetry run ruff check tests/test_models.py` clean.
Next: T064.
Watch: nothing.

## 2026-09-22T19:01:00+02:00 · Implementer US-5 · T064

Did: nothing to generate. `ip_address` was added to `Acceptance` by this feature's first
story, with its `verbose_name` and `help_text` already carrying the Article XV
justification, and this story's own change to `record()` is behavioural only — no field,
option or constraint changed. There is no schema for a migration to capture.
Verified: `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django
makemigrations --check --dry-run` — "No changes detected", exit 0, checked across every
installed app, not `mvp_compliance` alone. `DJANGO_SETTINGS_MODULE=tests.settings poetry
run python -m django makemigrations` (without `--dry-run`, to be sure nothing was merely
suppressed) — "No changes detected", exit 0.
Next: T065.
Watch: nothing.

## 2026-09-22T19:05:00+02:00 · Implementer US-5 · T065

Did: added an *Optional evidence* subsection to `docs/models.md` under `Acceptance`,
naming `MVP_COMPLIANCE_RECORD_IP_ADDRESS`, its default of `False`, what it holds, that
only `REMOTE_ADDR` is ever read and why `X-Forwarded-For` and every other forwarded
header is refused, the empty-field behaviour with no request supplied, and that a
setting change never touches an existing record. Extended the README's `Acceptance`
paragraph with the same setting, its default, and the call shape. Neither story before
this one had added a CHANGELOG entry for this feature, so this task wrote the whole
`### Added` block for it — the `Acceptance` model and `record()`, immutability,
`outstanding_for()`, the account-removal setting, and this story's optional-evidence
setting, each in plain language, with the IP setting's entry naming the personal data
it holds and stating that it is off unless a project deliberately turns it on.
Verified: both new documented examples (the request-supplied and no-request calls under
the setting) executed against a real test database — a scratch pytest module
(`tests/test_docs_scratch.py`) covering both as documented; passed, removed afterwards.
Diffed the whole story's changes against the verified base (`c0ee7e0`) and confirmed no
new `gettext_lazy` string was introduced anywhere, so the message catalogue needs no
regeneration. `poetry run pytest tests/ -q` — 198 passed (193 at the base plus this
story's 5 new tests). `poetry run ruff check .` clean.
Next: this story's own completion report.
Watch: nothing.

## 2026-09-22T22:20:00+02:00 · Orchestrator · US-5 accepted

Did: receipts matched the brief, 198 tests green, no migration outstanding, catalogue clean with no
fuzzy entry. Swept the whole feature diff for a forwarded-header read — every mention is prose
explaining the refusal, and the only `request.META` read in the package is `REMOTE_ADDR`. Probed the
setting gate by deleting it from `record()`: the suite stayed green, because the defaults test
records without a request and so never exercises the gate at all. Added the case that does — a
request in hand with the setting off, which is what an ordinary sign-in flow produces — and checked
it against the defect: with the gate removed it fails on the recorded address. D18 records it.
Verified: 199 tests pass with randomisation and parallelism off, `pre-commit run --all-files` green
on a cleared cache, `makemigrations --check` clean across every app.
Next: convergence — squash this branch's migrations into one, regenerate the catalogue, cleanup pass,
ADR verdicts. Then the review gate.
Watch: nothing.
