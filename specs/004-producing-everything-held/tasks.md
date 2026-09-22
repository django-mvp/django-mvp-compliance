# Tasks — 004 Producing everything held about one person's acceptances

Derived from [plan.md](./plan.md). Task ids are stable and are what `feature-state.json` tracks.
Every task follows Article I: the failing test comes first.

Documentation is not batched into a closing story. Each public name is documented in the story that
introduces it, so `forge verify`'s docs step is a real signal at every story boundary rather than
only at the last one.

## Foundational — none

Everything this feature reads is on main from FS-001 and FS-003. The two fixtures the route tests
need depend on a permission that does not exist until US-3, so they belong to that story.

## US-1 — Everything held about one person, in one answer (P1, issue #30)

| Id | Task | Done when |
|---|---|---|
| T001 | `tests/test_records.py::TestProduce` — a person with acceptances across several documents: the answer contains every one of them, each naming the document, the version number and the moment (scenarios 1, 2, FR-001, FR-002, FR-003) | Fails for the right reason before T004 |
| T002 | `tests/test_records.py::TestProduce::test_it_contains_nothing_belonging_to_anybody_else` — three people with acceptances, an answer produced for one, and nothing in it belongs to the others (scenario 3, FR-004, SC-001) | Fails before T004 |
| T003 | `tests/test_records.py::TestProduce::test_every_acceptance_of_one_document_appears` — several acceptances of one document over time and all of them are present, not only the most recent (scenario 4, FR-002) | Fails before T004 |
| T004 | `mvp_compliance/records.py` — `AcceptanceEntry`, `Section` and `PersonalRecord` as frozen dataclasses per plan.md, and `produce(subject)` building one from `Acceptance.objects.for_subject(subject).select_related("version", "version__document")`. Module docstring saying the answer is assembled and never stored, and that the package holds one kind of record today. `wording` is left to T011 | T001–T003 pass |
| T005 | `tests/test_records.py::TestProduce::test_a_person_with_no_records_gets_an_answer` — an answer for a subject the package holds nothing about reports `is_empty`, carries its section shape, and raises nothing (scenario 5, FR-005, SC-005) | Passes |
| T006 | `tests/test_records.py::TestProduce::test_the_same_answer_twice` — produce twice with no change to the records and assert the two answers are equal, which the frozen dataclasses make an ordinary comparison (scenario 6, FR-006) | Passes, and no attribute of the answer is a clock reading |
| T007 | `tests/test_records.py::TestProduce::test_it_costs_a_fixed_number_of_queries` — `django_assert_num_queries` around an answer for a person with acceptances across two documents and then across ten, asserting the same count (SC-008) | Passes; the count does not move with the number of documents |
| T008 | `tests/test_records.py::TestProduce::test_a_further_kind_of_record_would_not_change_the_answer` — assert the answer's own field names are exactly `{"subject", "sections"}`, so a kind of record can only join as a section (FR-017) | Passes |
| T009 | `docs/models.md` — a *Producing what is held* subsection: `produce()`, what an entry names, and that nothing is stored. `README.md` gains the call in its surface list | `forge verify` docs step green on the branch |

## US-2 — The wording they were shown, alongside each record (P1, issue #31)

| Id | Task | Done when |
|---|---|---|
| T010 | `tests/test_records.py::TestWording` — every entry carries the wording served for the version it names, and it is identical to what was stored at publication (scenarios 1, 3, FR-007, SC-002) | Fails before T011 |
| T011 | `mvp_compliance/records.py` — `wording` on `AcceptanceEntry`, read from `Version.html`. A comment says it is the HTML stored at publication and never produced again, because a renderer upgrade or an allow-list change would make the answer show something nobody was served (Article XIII, FR-010) | T010 passes |
| T012 | `tests/test_records.py::TestWording::test_a_superseded_versions_wording_is_the_superseded_one` — publish a version, record an acceptance, publish a later version of the same document, and assert the entry carries the earlier wording rather than what is now in force (scenario 2, FR-008) | Passes |
| T013 | `tests/test_records.py::TestWording::test_each_entry_carries_its_own_versions_wording` — a person with acceptances of three versions of one document, and each entry's wording is that version's, with no entry borrowing another's (scenario 4, FR-009) | Passes |
| T014 | `tests/test_records.py::TestWording::test_nothing_is_rendered_when_an_answer_is_produced` — write a stored `html` that the configured renderer would not produce from the same markdown, produce the answer, and assert the entry carries the stored text. The renderer is never called on this path (FR-010) | Passes, and the assertion is on the produced text rather than on a mock's call count alone |
| T015 | `docs/models.md` — the wording guarantee in the subsection T009 added: each entry carries the version's own stored wording, in full | Docs step green |

## US-3 — Only the people who should can produce it (P1, issue #32)

| Id | Task | Done when |
|---|---|---|
| T020 | `tests/test_records.py::TestNamingAPerson` — `resolve_subject()` resolves an account's login name and an account's email address to that account's identifier, resolves text matching neither to itself, and is case-insensitive on the email (`research.md` R3) | Fails before T021 |
| T021 | `mvp_compliance/records.py` — `resolve_subject(text)` with the resolution order from plan.md. A comment names the ambiguity it accepts and says the produced answer reports the subject it was produced for, so a reader can see which reading was taken | T020 passes |
| T022 | `mvp_compliance/models.py` — `Disclosure`, a proxy of `Acceptance` with no fields, `Meta.proxy = True`, `verbose_name`, `verbose_name_plural`, and `permissions = [("produce_disclosure", …)]`. A class docstring says it carries no table and exists so the act has a name in the admin index, an address and a permission of its own. `makemigrations mvp_compliance` | `makemigrations --check` clean; migrate-from-zero reaches the same final state |
| T023 | `tests/test_admin.py::TestDisclosureRefusals` — one test per route and caller, none left untested (SC-003): not signed in, signed in and not staff, and staff holding every other permission this package defines including `view_disclosure`. Each is refused and reaches no answer (scenarios 2, 3, FR-012) | Fails before T026 |
| T024 | `tests/test_admin.py::TestDisclosureRefusals::test_a_refusal_reveals_nothing` — the refusal for a person with records and the refusal for a person with none are the same status and the same body (scenario 4, FR-013, SC-004) | Fails before T026 |
| T025 | `tests/test_admin.py::TestDisclosureRefusals::test_the_permission_is_held_by_nobody_on_installation` — a freshly created account, and a freshly created account made staff, hold `produce_disclosure` in neither case; the permission exists and is granted deliberately (scenario 5, FR-011) | Fails before T026 |
| T026 | `mvp_compliance/forms.py` — `DisclosureForm` with one field for the person, `help_text` saying what may be typed into it. `mvp_compliance/admin.py` — `DisclosureAdmin` per plan.md: both view hooks keyed on `produce_disclosure`, all three write hooks `False`, and `changelist_view()` replaced outright, raising `PermissionDenied` itself before anything about the named person is read | T023–T025 pass |
| T027 | `tests/conftest.py` — a `disclosure_producer` fixture (staff holding only `produce_disclosure`) and an `everything_else` fixture (staff holding every permission this package defines except it, including `view_disclosure`), both built on `grant()` | Used by the tests above instead of inline construction |
| T028 | `tests/test_admin.py::TestDisclosurePage` — somebody holding the permission reaches the page, asks about a person, and the answer names every acceptance with its document, version, moment and wording in full; asking about a person with no records gives the page saying nothing is held (scenario 1, FR-001, FR-005, FR-007) | Fails before T029 |
| T029 | `mvp_compliance/templates/admin/mvp_compliance/disclosure/produce.html` and `…/acceptances.html` per plan.md — the field, the subject the answer was produced for, a loop over sections each including its own partial, and the entries with their wording marked safe. Every string translatable | T028 passes |
| T030 | `tests/test_admin.py::TestDisclosurePage::test_the_page_offers_no_way_to_change_anything` — the page carries no add, change or delete control, and the admin index entry appears for the permission holder and not for anybody else | Passes |
| T031 | `tests/test_app.py` — the proxy is registered in the admin and `Acceptance` itself is not, so there is no changelist of anybody's records; `mvp_compliance.urls` still does not exist | Passes |
| T032 | `docs/disclosure.md` — new: the page, its address, the permission and that it is held by nobody until granted, what may be typed into the field, what the answer contains, and that producing one is not recorded. `README.md` — the page in its surface list and the new page in its documentation list | Docs step green |

## US-4 — An answer for a person whose account is gone (P2, issue #33)

Expected to need no production code: `produce()` filters on `subject`, the identifier FS-003 writes
once and never clears. The tasks below prove that rather than assume it, and the reviewer is asked
to confirm the claim holds in the code.

| Id | Task | Done when |
|---|---|---|
| T040 | `tests/test_records.py::TestSurvivingRecords` — record acceptances for a person, remove their account under the package's default, and assert their acceptances are in the answer, each still naming the person, the version and the moment and carrying the wording served (scenarios 1, 2, FR-014, SC-006) | Passes against the code US-1 to US-3 left, with no change to it |
| T041 | `tests/test_records.py::TestSurvivingRecords::test_the_other_setting_leaves_nothing_to_produce` — with `MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL` off under `override_settings`, removing the account leaves an answer saying nothing is held (scenario 3) | Passes |
| T042 | `tests/test_records.py::TestSurvivingRecords::test_a_mix_of_people_with_and_without_accounts` — people with and without accounts, an answer produced for one of them, and nothing in it belongs to anybody else (scenario 4, FR-004) | Passes |
| T043 | `tests/test_admin.py::TestDisclosurePage::test_a_person_whose_account_is_gone` — the same through the page, asked for by the identifier the records carry, which is the only way that person can be named (US-4, `research.md` R3) | Passes |
| T044 | `docs/disclosure.md` — how to ask about somebody whose account has been removed, and that what survives is FS-003's setting rather than this page's behaviour | Docs step green |

## US-5 — The answer says what it covers, and what it does not (P1, issue #34)

| Id | Task | Done when |
|---|---|---|
| T050 | `tests/test_records.py::TestCoverage` — every answer carries a statement that it covers what this package holds and not data held elsewhere in the project, and an answer holding nothing carries the same statement (scenarios 1, 2, FR-015, SC-005) | Fails before T051 |
| T051 | `mvp_compliance/records.py` — `coverage` on `PersonalRecord`, translated, carried by the answer rather than only by the page so a later route carries it too | T050 passes |
| T052 | `tests/test_admin.py::TestDisclosurePage::test_the_page_states_what_it_covers` — the statement is on the page in both states, near the answer rather than in a footer (FR-015) | Fails before T053 |
| T053 | The templates from T029 — the statement rendered in both states | T052 passes |
| T054 | `tests/test_admin.py::TestUserFacingStrings` — extend the existing catalog sweep so no string this package shows names a regulation or claims an answer is complete (scenario 3, FR-016, SC-007). The list of names is in the test, and the sweep reads the shipped catalog so a string added later is covered without anybody remembering | Passes, and reinstating a claiming string makes it fail |
| T055 | `tests/test_records.py::TestCoverage::test_the_documentation_claims_nothing_either` — sweep `docs/disclosure.md` and the README section this feature added for the same names and claims (SC-007) | Passes |
| T056 | `CHANGELOG.md` — the Added entry for this feature: the page, the permission, and that producing an answer stores nothing and is not recorded | Docs step green |

## Closing — Forge, at convergence

| Id | Task | Done when |
|---|---|---|
| T060 | Squash the branch's migrations into one `0004_*` file. `0001`–`0003` are on main and are not touched | `makemigrations --check` clean, migrate-from-zero reaches the same final state, full suite green |
| T061 | Regenerate `mvp_compliance/locale/en/LC_MESSAGES/django.po` over the new strings, from the repository root with `--no-obsolete` | `makemessages` clean, no fuzzy entry left carrying another string's text |
| T062 | `demo/management/commands/seed_demo.py` — seed acceptances, including one whose account is then removed, and an account holding `produce_disclosure`, so every state the page can be in is reachable on the demo | Seeding twice changes nothing; every state in the walkthrough is reachable |
| T063 | Cleanup pass over the feature diff (`craft-simplify`), inside this feature's blast radius | The touched code is no noisier than it was |
| T064 | ADR verdict recorded in place for every `## D<n>` in `decisions.md` | `forge check-adrs` green |
