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
