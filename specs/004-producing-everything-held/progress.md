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
