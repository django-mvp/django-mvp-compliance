# Progress — 004 Producing everything held about one person's acceptances

The running log of this feature's implementation run. The ledger
(`feature-state.json`) is the machine record; this is the readable one.

---

## 2026-09-23 — S3 PLAN

Picked off the feature queue as the one feature ready to build in this repo. Branch
`004-producing-everything-held` cut from `origin/main` at `096c4dd`, which already carries the
specification merged in #29 and FS-001, FS-002 and FS-003 in full.

**Spec re-read against what landed since it was written.** The specification was written when
FS-001 and FS-003 were specified and not yet delivered, and says so in its own assumptions. Read
against the three specifications delivered since:

- FS-001 fixes each version's rendered output at publication and forbids producing it again
  (FR-015, FR-016), which is what FR-007 and FR-010 here rely on. Unchanged.
- FS-002 is the authoring surface and touches nothing this feature reads.
- FS-003 holds the acceptance, the identifier that survives an account's removal, and the setting
  that governs whether it survives — the three things US-4 rests on. Unchanged.

No contradiction, so nothing to put to Sam.

Wrote `research.md` (eight questions), `plan.md` and `tasks.md`. The design is one function, one
page and one permission, and it stores nothing.

## 2026-09-22T22:33:27Z · Implementer US-1 · T001-T004

**Did**: Wrote the three RED tests for `produce()` (`TestProduce::test_the_answer_contains_every_acceptance_with_its_document_version_and_moment`,
`::test_it_contains_nothing_belonging_to_anybody_else`, `::test_every_acceptance_of_one_document_appears`),
confirmed each failed on `ModuleNotFoundError: No module named 'mvp_compliance.records'` (the module
did not exist), then wrote `mvp_compliance/records.py`: `AcceptanceEntry`, `Section`,
`PersonalRecord` as frozen dataclasses and `produce(subject)` over
`Acceptance.objects.for_subject(subject).select_related("version", "version__document")`.
`wording` left off `AcceptanceEntry` per the brief — that is US-2's T011.

**Verified**: `poetry run pytest tests/test_records.py -v` → 3 passed. `poetry run ruff check
mvp_compliance/records.py tests/test_records.py` → all checks passed. `poetry run mypy
mvp_compliance/records.py` → no issues. `poetry run python manage.py makemigrations --check
--dry-run` → no changes detected (this module adds no model). Demonstrates SC-001 (nothing
belonging to anybody else), FR-001/002/003.

**Next**: T005-T008 — the empty answer, equality across two productions, the fixed query count,
and the `{subject, sections}` field-name guarantee.

**Watch**: none.

## 2026-09-22T22:34:37Z · Implementer US-1 · T005-T008

**Did**: Added four more assertions against the `produce()` built in T004, none of which needed a
production-code change: `test_a_person_with_no_records_gets_an_answer` (an unknown subject gets
`is_empty is True` and an empty entries tuple, never an exception), `test_the_same_answer_twice`
(patches `django.utils.timezone.now` mid-test and asserts both `first == second` and
`now.call_count == 0` — proof, not inference, that `produce()` reads no clock, D11),
`test_it_costs_a_fixed_number_of_queries` (`django_assert_num_queries(1)` at two documents and
again at ten, same count both times), and `test_a_further_kind_of_record_would_not_change_the_answer`
(`dataclasses.fields(PersonalRecord)` names exactly `{"subject", "sections"}`).

**Verified**: `poetry run pytest tests/test_records.py -v` → 7 passed. `poetry run ruff check
tests/test_records.py mvp_compliance/records.py` → all checks passed. `poetry run mypy
mvp_compliance/records.py` → no issues found. Demonstrates FR-005/SC-005, FR-006, SC-008, FR-017.

**Next**: T009 — `docs/models.md` and `README.md`.

**Watch**: none.

## 2026-09-22T22:36:38Z · Implementer US-1 · T009

**Did**: Added a "Producing what is held" subsection to `docs/models.md`, after `## \`Acceptance\``'s
existing subsections: `produce(subject)`, what `PersonalRecord`, `Section` and `AcceptanceEntry`
name, that a person with no records gets a normal answer, and that nothing is stored. Added one
sentence to README.md's status callout naming `mvp_compliance.records.produce(subject)`.

**Verified**: `poetry run python <kit>/forge verify --repo . --steps docs --base ee871bf` →
`[verify] docs: passed (0s)`. This is the mechanical check named in T009's "Done when" — it flags a
public name a branch adds that no page quotes as code, and confirmed all four (`AcceptanceEntry`,
`Section`, `PersonalRecord`, `produce`) are covered.

**Next**: US-1 complete (T001-T009). Ran the story's full narrow scope
(`poetry run pytest tests/test_records.py -v`) once more: 7 passed. The full repo verify runs once,
at the end of the story, per the Implementer protocol.

**Watch**: `feature-state.json`'s `stories[].status` for US1 is left `"todo"` — flipping it is
Forge's, not this Implementer's, per the brief's prohibitions.

## 2026-09-22T22:52:00Z · Forge · US-1 acceptance

**Did**: Regenerated `mvp_compliance/locale/en/LC_MESSAGES/django.po` over the one string this
story adds, stripped the `POT-Creation-Date` line and un-fuzzied the entry `makemessages` had
guessed was a rewording of `acceptances` and filled with that entry's text. Strengthened
`test_it_contains_nothing_belonging_to_anybody_else` so each person accepts a different document —
as written, three people accepting the same version produced indistinguishable entries, so a leak
would have passed the count assertion.

**Verified**: `forge verify --base ee871bf` green on every step. `forge tamper-check --base
ee871bf` clean. Reinstated the defect the isolation test guards (dropped the `for_subject` filter)
and confirmed the test fails, then restored and confirmed 7 pass.

**Decided**: the catalog is regenerated in the story that adds a string, not at convergence. The
sweep in `tests/test_admin.py::TestUserFacingStrings` reads the shipped catalog, so a story that
adds a translatable string and leaves the catalog alone hands back a red suite. The US-1 brief said
the opposite and was wrong; `tasks.md` T061 is now a check rather than the work, and every brief
from US-2 on carries the correction.

**Next**: US-2 — the wording served, alongside each record.
