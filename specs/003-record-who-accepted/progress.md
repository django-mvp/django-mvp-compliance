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
