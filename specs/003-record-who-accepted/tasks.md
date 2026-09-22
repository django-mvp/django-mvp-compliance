# Tasks — 003 The record of who accepted which version

Derived from [plan.md](./plan.md). Task ids are stable and are what `feature-state.json` tracks.
Every task follows Article I: the failing test comes first.

Documentation is not batched into a closing story. Each public name is documented in the story that
introduces it, so `forge verify`'s docs step is a real signal at every story boundary rather than
only at the last one.

## Foundational — sequential, before any story

| Id | Task | Done when |
|---|---|---|
| T001 | `tests/factories.py` — `UserFactory` over `django.contrib.auth.get_user_model()`, `factory.Sequence` on the username field, no variant subclasses. `tests/test_factories.py` asserts it builds a valid saved user and that two builds do not collide | Both pass; Article X's one-factory-per-model rule holds |
| T002 | `tests/conftest.py` — a `user` fixture, a thin wrapper over `UserFactory` | Used by the modules below instead of inline construction |

## US-1 — One acceptance, written down and left alone (P1, issue #24)

| Id | Task | Done when |
|---|---|---|
| T010 | `tests/test_models.py::TestAcceptance` — recording a user's acceptance of a published version produces a record naming that user, that version and the moment it happened; the record's concrete field names are exactly `{"id", "user", "subject", "version", "accepted_at", "ip_address"}`, so nothing can be added to it without the test saying so (scenario 1, FR-001, Article XV) | Fails for the right reason before T013 |
| T011 | `tests/test_models.py::TestAcceptance::test_no_way_to_accept_a_document` — assert `Acceptance` has no field or manager method that takes a `Document`, and that `record()` refuses one (scenario 6, FR-002) | Fails before T013 |
| T012 | `tests/test_models.py::TestRecording` — recording against a never-published version is refused with `RecordError` and writes nothing; recording for a user with no primary key is refused the same way; a superseded version is accepted rather than refused (scenario 5, FR-003, D2) | Fails before T014 |
| T013 | `mvp_compliance/models.py` — `Acceptance` with `user` (`ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="compliance_acceptances")`, `on_delete=SET_NULL` for now — US-4 replaces it with the callable), `subject` (`CharField(max_length=255, editable=False)`), `version` (`ForeignKey(Version, on_delete=PROTECT, related_name="acceptances")`), `accepted_at` (`DateTimeField(editable=False)`), `Meta.verbose_name`/`verbose_name_plural`, `__str__`, and a class docstring saying the record is finished once written. `verbose_name` and `help_text` on every field, each wrapped with `gettext_lazy`; `subject`'s `help_text` carries the Article XV justification from plan.md | T010 and T011 pass |
| T014 | `mvp_compliance/models.py` — `Acceptance.subject_of(user)` as a `staticmethod` returning `str(user.pk)` and raising `RecordError` when the user has no primary key; `AcceptanceManager.record(user, version, request=None)` refusing a draft version, deriving the subject, and creating the row with `accepted_at = timezone.now()` | T012 passes |
| T015 | `mvp_compliance/exceptions.py` — `RecordError` and `RecordedAcceptanceError`, each with a docstring naming the requirement it holds. `tests/test_exceptions.py` asserts neither subclasses `ValidationError`, matching the existing assertions for the other two | Its own tests pass |
| T016 | `tests/test_models.py::TestAcceptanceImmutability` — one test per refused route, none left untested (SC-001): `save()` on an existing row, `AcceptanceQuerySet.update()`, `bulk_update()`, `Acceptance.delete()`, `AcceptanceQuerySet.delete()`. Each asserts `RecordedAcceptanceError` **and** that the stored row is unchanged afterwards (scenarios 2 and 4, FR-004, FR-005, FR-006) | Fails before T017 |
| T017 | `mvp_compliance/models.py` — `AcceptanceQuerySet` refusing `update()` whenever it matches anything and refusing `delete()` outright; `Acceptance.save()` refusing when the database already holds the row, asked of the database rather than of Django's adding flag; `Acceptance.delete()` refusing. `AcceptanceManager.use_in_migrations = True`, and the manager forwards each queryset method it needs explicitly (the shape `VersionManager` already uses, for the reason in `specs/001-legal-documents-kept/decisions.md` D21) | T016 passes |
| T018 | `tests/test_migrations.py` — extend the existing assertion so no shipped migration writes to an acceptance either, and `tests/test_models.py::TestAcceptanceImmutability::test_a_historical_model_inherits_the_guard` proves a historical `Acceptance` from the migration state carries `AcceptanceManager` (scenario 3, FR-004) | Passes |
| T019 | `tests/test_models.py::TestAcceptance::test_record_still_points_at_the_version_it_named` — an acceptance of a version that is later superseded still points at that version and is unchanged (scenario 7, FR-007) | Passes |
| T020 | `tests/factories.py` — `AcceptanceFactory`, one per model, `factory.SubFactory` on `user` and `version`, `accepted_at` supplied. `tests/test_factories.py` asserts it builds a valid instance. `tests/conftest.py` gains an `acceptance` fixture | Both pass |
| T021 | `makemigrations mvp_compliance` | `makemigrations --check` clean, migrate-from-zero reaches the same final state |
| T022 | `docs/models.md` — an `Acceptance` section: what the record is, `Acceptance.objects.record()`, that a draft is refused, and the immutability table in the style the `Version` section already uses. `README.md` gains the model in its surface list | `forge verify` docs step green on the branch |

## US-2 — A later version is a second record, not an update (P1, issue #25)

| Id | Task | Done when |
|---|---|---|
| T030 | `tests/test_models.py::TestRecording` — a person who accepts a later version of the same document ends with two records and the earlier one is byte-for-byte what it was; their acceptances list in the order they happened; two people each accepting the same version get their own record (scenarios 1, 2, 4, FR-008, SC-002) | Fails before T032 |
| T031 | `tests/test_models.py::TestRecording::test_the_same_version_twice_leaves_one_record` — recording the same person's acceptance of the same version again returns the existing record, does not raise, and leaves exactly one row (scenario 3, FR-009, D3) | Fails before T032 |
| T032 | `mvp_compliance/models.py` — the `one_acceptance_per_person_per_version` unique constraint over `subject` and `version`; `record()` switched to `get_or_create()` over that constraint; `Meta.ordering = ["accepted_at", "id"]`. A comment at the constraint says why it is over `subject` rather than `user`: it has to hold for a record whose account is gone | T030 and T031 pass |
| T033 | `tests/test_models.py::TestRecording::test_a_second_row_is_refused_by_the_database` — force a duplicate past `record()` and assert `IntegrityError`, so the constraint rather than the method is what holds FR-009 | Passes |
| T034 | `tests/test_models.py::TestRecording::test_two_recordings_leave_one_record` — two recordings of the same person and version, and exactly one record exists afterwards (scenario 5, FR-010, SC-003) | Passes without wall-clock timing or thread scheduling |
| T035 | `makemigrations mvp_compliance` | `makemigrations --check` clean |
| T036 | `docs/models.md` — the repeat and the later-version behaviour in the `Acceptance` section, stated as what happens rather than as an API note | Docs step green |

## US-3 — Asking what a person still owes (P1, issue #26)

| Id | Task | Done when |
|---|---|---|
| T040 | `tests/test_models.py::TestOutstanding` — for one person and one document: nothing outstanding when they have accepted the version in force; outstanding when they have never accepted anything; outstanding when they accepted a version that has since been superseded; not outstanding when the document has never published anything (scenarios 1, 2, 3, 5, FR-011) | Fails before T042 |
| T041 | `tests/test_models.py::TestOutstanding` — across several documents the answer names exactly the documents whose version in force this person has not accepted and no others; a person with nothing outstanding gets an empty result and not an error (scenarios 4, 6, FR-012, SC-004) | Fails before T042 |
| T042 | `mvp_compliance/models.py` — `DocumentQuerySet.outstanding_for(user)` per plan.md, `DocumentManager` exposing it, and `Document.is_outstanding_for(user)` implemented as that queryset narrowed to `self.pk` rather than as a second expression of the rule | T040 and T041 pass |
| T043 | `tests/test_models.py::TestOutstanding::test_the_answer_costs_a_fixed_number_of_queries` — `django_assert_num_queries` around the answer for a person across two documents and then across ten, asserting the same count (scenario 7, FR-018, SC-005) | Passes; the count does not move with the number of documents |
| T044 | `docs/models.md` — an *Outstanding* subsection: both entry points, that a document with nothing in force is never outstanding, and that this answer is deliberately unfiltered by whether a site enforces a document | Docs step green |

## US-4 — Records outlive the accounts they name (P2, issue #27)

| Id | Task | Done when |
|---|---|---|
| T050 | `tests/test_models.py::TestAccountRemoval` — under the package's default, removing an account leaves that person's acceptances in place, each still naming whose it is and still pointing at the version accepted (scenarios 1, 2, FR-013, FR-014, SC-006) | Fails before T052 |
| T051 | `tests/test_models.py::TestAccountRemoval` — with the setting turned off under `override_settings`, removing an account leaves none of that person's acceptances; under either setting no other person's records are affected (scenarios 4, 5, FR-015, SC-007) | Fails before T052 |
| T052 | `mvp_compliance/models.py` — `keep_or_remove_acceptances(collector, field, sub_objs, using)` reading `MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL` (default `True`) and delegating to Django's `SET_NULL` or `CASCADE`; `Acceptance.user.on_delete` switched to it. A comment says the setting is read per delete rather than per process, which is what makes it a setting; that the field stays `null=True` because the system check for `SET_NULL` compares by identity and will not fire for a callable; and that a `lazy_sub_objs` attribute on the callable together with `Meta.base_manager_name` naming `AcceptanceManager` would route the update through `AcceptanceQuerySet.update()`'s refusal and break the default, while neither alone does anything (`research.md` R1) | T050 and T051 pass |
| T053 | `tests/test_models.py::TestAccountRemoval::test_a_surviving_record_is_still_found_with_its_siblings` — after the account is gone, `Acceptance.objects.for_subject()` returns that person's records together and in order (scenario 3, FR-014) | Fails before T054 |
| T054 | `mvp_compliance/models.py` — `AcceptanceQuerySet.for_subject(subject)` and `AcceptanceManager.for_person(user)` as a thin call through `subject_of()` into it | T053 passes |
| T055 | `tests/test_models.py::TestAccountRemoval::test_a_recreated_account_inherits_nothing` — remove an account, create another with the same username, and assert the new one has no acceptances (the spec's edge case, and what `subject` being the primary key buys) | Passes |
| T056 | `makemigrations mvp_compliance` | `makemigrations --check` clean |
| T057 | `docs/models.md` and `README.md` — the setting, its default, how to find a person's records after the account is gone, and the default's cost stated plainly: closing an account does not remove what this package holds about that person (D1) | Docs step green |

## US-5 — Nothing held about a person that the site did not ask for (P2, issue #28)

| Id | Task | Done when |
|---|---|---|
| T060 | `tests/test_models.py::TestOptionalEvidence` — with the package's defaults an acceptance holds the person, the version and the time and nothing else; with `MVP_COMPLIANCE_RECORD_IP_ADDRESS` on and a request supplied, the address is held alongside them (scenarios 1, 2, FR-016, SC-008) | Fails before T062 |
| T061 | `tests/test_models.py::TestOptionalEvidence` — records made before the setting was turned on are unchanged and hold none of it, and records made while it was on still hold what they held after it is turned off again (scenarios 3, 4, FR-017) | Fails before T062 |
| T062 | `mvp_compliance/models.py` — `ip_address` (`GenericIPAddressField(null=True, blank=True)`, `verbose_name`, `help_text` carrying the Article XV justification), and `record()` reading `request.META.get("REMOTE_ADDR")` when the setting is on and a request was supplied. A comment says the package reads `REMOTE_ADDR` and refuses to parse `X-Forwarded-For`, because that header is set by the client and the deployment is the only thing that knows which proxies to trust (`research.md` R6) | T060 and T061 pass |
| T063 | `tests/test_models.py::TestOptionalEvidence::test_no_request_holds_no_address` — with the setting on and no request supplied, the field is empty and recording succeeds, so a management command or a shell session needs no invented value | Passes |
| T064 | `makemigrations mvp_compliance` | `makemigrations --check` clean |
| T065 | `README.md` and `docs/models.md` — the setting, its default of off, and what it holds. `CHANGELOG.md` — the Added entry for this feature, naming in plain language the personal data the optional setting holds, per Article XV | Docs step green |

## Closing — Forge, at convergence

| Id | Task | Done when |
|---|---|---|
| T070 | Squash the branch's migrations into one `0003_*` file. `0001_initial.py` and `0002_version_publish_permission.py` are on main and are not touched | `makemigrations --check` clean, migrate-from-zero reaches the same final state, full suite green |
| T071 | Regenerate `mvp_compliance/locale/en/LC_MESSAGES/django.po` over the new strings, from the repository root with `--no-obsolete` | `makemessages` clean, no fuzzy entry left carrying another string's text |
| T072 | Cleanup pass over the feature diff (`craft-simplify`), inside this feature's blast radius | The touched code is no noisier than it was |
| T073 | ADR verdict recorded in place for every `## D<n>` in `decisions.md` | `forge check-adrs` green |
