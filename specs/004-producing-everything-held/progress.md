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

## 2026-09-23T00:50:00+02:00 · Implementer US-2 · T010-T015

**Did**: Added `TestWording` to `tests/test_records.py` (T010's
`test_the_wording_is_what_was_stored_at_publication`, confirmed it failed with
`AttributeError: 'AcceptanceEntry' object has no attribute 'wording'` before T011), then
`mvp_compliance/records.py` gained `wording: str` on `AcceptanceEntry`, read as
`acceptance.version.html` in `produce()` — the renderer is never imported or called from this
module (T011). T012-T013 (`test_a_superseded_versions_wording_is_the_superseded_one`,
`test_each_entry_carries_its_own_versions_wording`) passed immediately against T011's
implementation, as `tasks.md` expected. T014
(`test_nothing_is_rendered_when_an_answer_is_produced`) reused the existing
`tests.test_models.UppercaseRenderer` stand-in renderer via `override_settings`, per the
brief's own steer — a published version's stored `html` cannot be rewritten through any route,
so the test switches `MVP_COMPLIANCE_RENDERER` after publication and asserts the entry still
carries the wording stored at publication rather than what the new renderer would now produce
from the same markdown; it also passed immediately, confirming FR-010 already held. T015 added
the wording guarantee to `docs/models.md`'s "Producing what is held" subsection.

**Verified**: `poetry run pytest tests/test_records.py -q` — 12 passed. `poetry run ruff check`
and `poetry run ruff format --check` on both changed files — clean. `forge verify --repo . --steps
docs --base ee871bf` → `[verify] docs: passed (0s)`. No new translatable string was added, so no
`makemessages` run was needed this story.

**Next**: US-3 — only the people who should can produce it.

**Watch**: `mvp_compliance/models.py` and `mvp_compliance/rendering.py` were not touched, per the
brief's prohibitions — the wording is read from the `Version.html` field FS-001 already stores.

## 2026-09-23T01:00:00+02:00 · Implementer US-3 · T020-T022

**Did**: Added `TestNamingAPerson` to `tests/test_records.py` (T020: an account's login name, its
email case-insensitively, and text matching neither resolving to itself), confirmed it failed with
`ImportError: cannot import name 'resolve_subject'` before adding `resolve_subject(text)` to
`mvp_compliance/records.py` (T021) — the resolution order from `plan.md`'s "Naming a person": the
user model's `USERNAME_FIELD`, then `email` where the user model has one and exactly one account
matches, then the text itself. T022 added `Disclosure`, a proxy of `Acceptance` with no fields,
`Meta.permissions = [("produce_disclosure", ...)]`, and generated
`mvp_compliance/migrations/0004_disclosure.py`.

**Verified**: `poetry run pytest tests/test_records.py::TestNamingAPerson -x` — 4 passed.
`poetry run python manage.py makemigrations --check --dry-run` — no changes detected.
`poetry run pytest tests/test_models.py tests/test_app.py -q` — 98 passed (no regression from the
new proxy). `ruff check`/`ruff format --check` and `mypy` clean on both changed files.

**Watch**: T025's acceptance criterion — a fresh account holding `produce_disclosure` in neither
case — was already true the moment T022's migration landed, before any admin code exists. Verified
this is not a test-ordering accident: Django's `post_migrate` permission creation reads the
**migration-state** models built by the migration executor, not the live `models.py` — mutating
`Disclosure.Meta.permissions` to `[]` in the source file, with the migration left alone, still
produced the permission on `migrate`. Recorded so nobody "fixes" this by rewriting T025 to depend
on T026.

## 2026-09-23T01:20:00+02:00 · Implementer US-3 · T023-T027

**Did**: `TestDisclosureRefusals` in `tests/test_admin.py` — not signed in (T023, 302, the admin's
own login redirect), signed in and not staff (T023, 302), staff holding every other permission this
package defines including the proxy's own routine `view_disclosure` (T023, 403), a refusal for a
person with records and one for a person without them carrying the same status and body (T024,
built with `AcceptanceFactory()` against one subject and a made-up one against the other), and a
fresh account/fresh staff account holding `produce_disclosure` in neither case (T025 — already
green per the note above). Confirmed T023/T024 failed on `NoReverseMatch: ... disclosure_changelist
... not found` before implementing. `mvp_compliance/forms.py` gained `DisclosureForm` — one
`subject` field, `required=False`, `help_text` naming what may be typed into it.
`mvp_compliance/admin.py` gained `DisclosureAdmin`: `has_view_permission`/`has_module_permission`
keyed on `produce_disclosure` alone, the three write hooks `False`, `changelist_view()` replaced
outright — checks the permission and raises `PermissionDenied` itself before reading
`request.GET` at all, never calls `super()` (T026). T027 added `disclosure_producer` and
`everything_else` fixtures to `conftest.py`, built on the existing `grant()` helper, and refactored
T023/T024's inline `Permission.objects.filter(...)` construction onto `everything_else`.

**Verified**: `poetry run pytest tests/test_admin.py::TestDisclosureRefusals -q` — 5 passed, both
before and after the T027 refactor. `poetry run pytest tests/test_admin.py -q` — 76 passed
(`TestUserFacingStrings` required regenerating the catalog — `makemessages --locale en --no-obsolete
--ignore "mvp_compliance/static/*"`, `POT-Creation-Date` line removed, five new entries filled with
their own text, none marked fuzzy). `ruff`/`mypy` clean.

## 2026-09-23T01:45:00+02:00 · Implementer US-3 · T028-T032

**Did**: `TestDisclosurePage` in `tests/test_admin.py` — the answer names the document, version,
moment (compared via `formats.date_format(timezone.localtime(...), "DATETIME_FORMAT")`, matching
the template's own `|date` filter rather than a raw UTC compare) and wording in full for a person
with records, and a person with none gets a page saying so (T028) — confirmed both failed on
`TemplateDoesNotExist: admin/mvp_compliance/disclosure/produce.html` before adding
`mvp_compliance/templates/admin/mvp_compliance/disclosure/produce.html` (the form, the produced
subject, a loop over `record.sections` including each section's own template — no coverage
statement and no produced-at stamp, both out of scope per the brief) and `.../acceptances.html`
(document, version, moment, wording marked `|safe`, T029). T030's
`test_the_page_offers_no_way_to_change_anything` and T031's admin-registration additions to
`tests/test_app.py` (`Disclosure` registered, `Acceptance` is not, `mvp_compliance.urls` still
absent) both passed immediately — nothing in T026/T029 registers a changelist or exposes a write
control, and `test_it_registers_no_public_urls` was never touched. T032 added
`docs/disclosure.md` (the page, its address, the permission and that it starts held by nobody,
naming a person, what the answer contains, what it does not do) and updated `README.md`'s status
callout and documentation list.

**Verified**: `poetry run pytest tests/test_admin.py tests/test_app.py -q` — 85 passed. Catalog
regenerated a second time for the template strings (`Produce`, `Nothing is held about this
person.` — the latter came back `#, fuzzy` against `Everything held about a person`, corrected by
hand to its own text). `djlint --reformat` on both new templates. `ruff`/`mypy` clean throughout.

**Next**: US-3 complete (T020-T032). The story's own scope is green; `forge verify` runs once,
at the end, before the completion report.

**Watch**: `feature-state.json`'s story status is left as Forge set it, per the brief's
prohibitions.

## 2026-09-22T23:15:00Z · Forge · US-3 acceptance

**Did**: The page showed the document, the version, the moment and the wording, and left out the
address a record holds where a site turned that on — D12 and `plan.md` § The page both put it
there, and the story's own criteria enumerated the other four without it. Wrote the failing test,
confirmed it failed on the missing address, added the block to `acceptances.html` and regenerated
the catalog. Approved the two guardrail flags as D14: every removed line across both flagged test
modules is an import, and no assertion was weakened.

**Verified**: `forge verify --base ee871bf` green on every step. The new test fails without the
template block and passes with it.

**Next**: US-4 — an answer for a person whose account is gone.
