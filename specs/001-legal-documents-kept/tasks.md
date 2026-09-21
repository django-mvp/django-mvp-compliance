# Tasks — 001 Legal documents kept as versioned records

Derived from [plan.md](./plan.md). Task ids are stable and are what `feature-state.json` tracks.
Every task follows Article I: the failing test comes first.

## Foundational — sequential, before any story

| Id | Task | Done when |
|---|---|---|
| T001 | Add `markdown` and `nh3` to `[project] dependencies` in `pyproject.toml`, with the comment saying why each is there, and update `poetry.lock` | `poetry install` succeeds, `deptry` reports no missing and no unused dependency |
| T002 | Create `mvp_compliance/migrations/__init__.py` | The app is migration-enabled and `makemigrations mvp_compliance` writes into it |
| T003 | Add `tests/test_migrations.py` and `tests/factories.py` to `[tool.forge.conformance] non-mirror-paths` in `pyproject.toml`, beside the existing `tests/test_app.py` entry, with a comment naming the subject each one has instead of a module | `forge conformance` passes on the branch |

## US-1 — Several documents, each with its own history (P1, issue #7)

| Id | Task | Done when |
|---|---|---|
| T010 | `tests/test_models.py::TestDocument` — three documents with distinct names exist side by side, each reporting an empty version sequence; a fourth with a duplicate name is refused | Tests fail for the right reason before T012 |
| T011 | `tests/test_models.py::TestDocument::test_document_holds_no_wording` — assert `Document`'s concrete field names are exactly `{"id", "name"}`, so a text field cannot be added to it without the test saying so (US-1 scenario 4, FR-002) | Fails before T012 |
| T012 | `mvp_compliance/models.py` — `Document` with `name` only: `CharField(max_length=100, unique=True)`, `verbose_name`, `help_text`, `Meta.verbose_name`/`verbose_name_plural`, `__str__`, a class docstring saying it holds no wording | T010 and T011 pass |
| T013 | `tests/test_models.py::TestVersion` — versions added to a document come back in the order they were added; a version added to one document leaves the other's sequence untouched; `number` is assigned by the package and is 1, 2, 3 within each document independently | Fails before T014 |
| T014 | `mvp_compliance/models.py` — `Version` with `document` (`ForeignKey`, `on_delete=PROTECT`, `related_name="versions"`), `number` (`PositiveIntegerField(editable=False)`), `markdown` (`TextField`). `Meta.ordering = ["document", "number"]` and the `unique_version_number_per_document` constraint. `number` assigned in `save()` as `max+1` within the document when the row is new | T013 passes |
| T015 | `tests/factories.py` — `DocumentFactory` and `VersionFactory`, one per model, `factory.Sequence` on `name`, `factory.SubFactory` on `document`, no variant subclasses. `tests/test_factories.py` asserts each builds a valid instance and that two builds do not collide | Both pass; Article X's one-factory-per-model rule holds |
| T016 | `tests/conftest.py` — `document` and `draft` fixtures, thin wrappers over the factories | Used by the modules below rather than inline construction |
| T017 | `makemigrations mvp_compliance` | `makemigrations --check` clean, migrate-from-zero reaches the same state |

## US-2 — Publishing puts exactly one version in force (P1, issue #8)

| Id | Task | Done when |
|---|---|---|
| T020 | `tests/test_models.py::TestPublishing` — a new version is a draft, is not current, and is freely editable and freely discardable (scenarios 1–3) | Fails before T022 |
| T021 | `tests/test_models.py::TestPublishing` — publishing the first draft makes it current with nothing superseded; publishing a second makes it current and supersedes the first; exactly one version answers as current; publishing an already-published version is refused and nothing moves (scenarios 4–6, 9) | Fails before T023 |
| T022 | `mvp_compliance/models.py` — `Version.Status` (`draft`, `current`, `superseded`), the `status` field, `published_at` (`DateTimeField(null=True, blank=True, editable=False)`), `is_published`, and the `CheckConstraint` tying `status`, `published_at` and `html` to each other | T020 passes |
| T023 | `mvp_compliance/exceptions.py` — `PublishError` and `PublishedVersionError`, each with a docstring saying which requirement it holds. `tests/test_exceptions.py` asserts neither subclasses `ValidationError` (D9) | T023's own tests pass |
| T024 | `mvp_compliance/models.py` — `Version.publish()` per plan.md: refuse when not a draft, lock the document row, supersede the current version, become current, all inside `transaction.atomic()` | T021 passes |
| T025 | `mvp_compliance/models.py` — the `one_current_version_per_document` partial unique constraint. `tests/test_models.py::TestPublishing::test_second_current_row_is_refused_by_the_database` forces a second current row past `publish()` and asserts `IntegrityError` (FR-007, SC-002) | Test passes; the constraint, not the method, is what raises |
| T026 | `tests/test_models.py::TestPublishing::test_two_publishes_leave_one_version_in_force` — two publishes against the same document, and the document still reports exactly one current version (US-2 scenario 7) | Passes without wall-clock timing or thread scheduling |
| T027 | `tests/test_models.py::TestPublishing::test_no_reverse_operation_exists` — assert by name that `Version` has no `unpublish`, `revert`, `rollback`, `make_current` or `restore`, and that no queryset method offers them (FR-009, US-2 scenario 8) | Passes, and fails if a convenience is added later |
| T028 | `makemigrations mvp_compliance` | `makemigrations --check` clean |

## US-3 — A published wording can never change (P1, issue #9)

| Id | Task | Done when |
|---|---|---|
| T030 | `tests/test_models.py::TestImmutability` — one test per mutation route, per SC-003: `save()` after changing `markdown`; `objects.update(markdown=...)`; `objects.bulk_update([...], ["markdown"])`; `instance.delete()`; `objects.delete()`. Each asserts `PublishedVersionError` and that the stored wording is unchanged afterwards | All five fail before T031 |
| T031 | `mvp_compliance/models.py` — `PUBLISHED_FROZEN_FIELDS`, the `save()` guard reading the stored row rather than an in-memory snapshot, and `VersionQuerySet.update()`, `bulk_update()`, `delete()` plus `Version.delete()`, all raising `PublishedVersionError` | T030 passes |
| T032 | `mvp_compliance/models.py` — `VersionManager.use_in_migrations = True`, so a historical model inside a migration gets this queryset (D10) | Asserted by a test that builds the historical model through `apps.get_model` and confirms the manager type |
| T033 | `tests/test_migrations.py` — assert no migration this package ships writes to a published version: read every operation in `mvp_compliance/migrations/`, and fail on any `RunPython` or `RunSQL` (D10). The test carries a comment saying what to do when a legitimate data migration is eventually needed | Passes |
| T034 | `tests/test_models.py::TestImmutability::test_superseding_does_not_change_the_wording` — a version superseded by a later publish still holds its original `markdown` (scenario 3, FR-013) | Passes |
| T035 | `tests/test_models.py::TestImmutability` — deleting a document that holds versions raises `ProtectedError`; a document holding none deletes normally; discarding the only draft returns a document to that state (FR-014, D8, edge case 4) | Passes |
| T036 | `tests/test_models.py::TestImmutability::test_correcting_an_error_makes_a_new_version` — the erroneous version is still readable beside the correction (scenario 6, SC-007) | Passes |

## US-4 — What a reader will be served is fixed at publication (P2, issue #10)

| Id | Task | Done when |
|---|---|---|
| T040 | `tests/test_rendering.py::TestMarkdownRenderer` — headings, lists, emphasis, links and tables survive; `<script>`, `<style>`, `<iframe>`, an `onclick` attribute and a `javascript:` URL do not (FR-017, US-4 scenario 4) | Fails before T041 |
| T041 | `mvp_compliance/rendering.py` — `MarkdownRenderer` per plan.md: `extensions`, `allowed_tags`, `allowed_attributes`, `allowed_url_schemes` as class attributes, `render()` running `markdown` then `nh3.clean`. Module docstring stating Article XIII: this is called once, at publication | T040 passes |
| T042 | `mvp_compliance/rendering.py` — `get_renderer()`, resolving `MVP_COMPLIANCE_RENDERER` through `import_string` and defaulting to `MarkdownRenderer`. `tests/test_rendering.py::TestRendererSetting` covers the default and an override | Passes |
| T043 | `mvp_compliance/models.py` — `html` (`TextField(blank=True)`), and `publish()` renders into it before anything is written. A draft carries no `html` (FR-019, scenario 5) | `tests/test_models.py::TestPublishing` covers both |
| T044 | `mvp_compliance/models.py` — `publish()` refuses with `PublishError` when the rendered output is empty once whitespace is stripped, before the row is touched (FR-018, D7, edge case 6) | Test passes and the document is unchanged afterwards |
| T045 | `tests/test_models.py::TestPublishing::test_stored_html_survives_a_renderer_change` — publish, swap `MVP_COMPLIANCE_RENDERER` with `override_settings` for a renderer that produces something visibly different, re-read, assert the stored HTML is byte-identical (US-4 scenario 3, SC-004) | Passes |
| T046 | `tests/test_models.py::TestImmutability::test_published_html_cannot_be_changed` — `html` is in the frozen set, covered by the same five routes as `markdown` | Passes |
| T047 | `makemigrations mvp_compliance` | `makemigrations --check` clean |

## US-5 — Every version stays retrievable, forever (P2, issue #11)

| Id | Task | Done when |
|---|---|---|
| T050 | `tests/test_models.py::TestRetrieval` — a document with three published versions returns all three in order; a superseded version returns its original wording and its original stored HTML; the current version is exactly the one most recently published; drafts are absent from the published history (scenarios 1, 2, 3, 5) | Fails before T051 |
| T051 | `mvp_compliance/models.py` — `VersionQuerySet.published()`, `.drafts()` and `.current()`, and `Document.current` as a property returning the current `Version` or `None` | T050 passes |
| T052 | `tests/test_models.py::TestRetrieval::test_a_document_with_nothing_published_reports_no_version_in_force` — `document.current` is `None` and raises nothing (FR-008, SC-006, scenario 4) | Passes |
| T053 | `tests/test_models.py::TestRetrieval::test_one_version_by_its_number` — `document.versions.get(number=2)` returns that version (FR-021) | Passes |
| T054 | `tests/test_models.py::TestRetrieval::test_four_documents_do_not_interfere` — four documents each accumulating their own history, and no operation on one alters another (SC-001) | Passes |
| T055 | README — the model surface, the one setting, and what this feature does and does not provide | Article VI satisfied |
| T056 | CHANGELOG — an `### Added` entry under `## [Unreleased]` naming the two models, the two dependencies and the setting in plain language | Article VI satisfied |
| T057 | `tests/test_app.py` — assert the package still registers no admin, ships no forms, no views and no URLs (D5) | Passes |

## Closing — Forge, at convergence

Not in the ledger: these belong to S5 rather than to a story, and a story cannot be accepted while
they are outstanding.

| Id | Task | Done when |
|---|---|---|
| TC01 | Squash the branch's migrations into one `0001_initial.py` | Migrate-from-zero reaches the same final state, `makemigrations --check` clean, suite green |
| TC02 | `mvp_compliance/locale/en/LC_MESSAGES/django.po` — `makemessages -l en` over the package | The catalog exists and CI's i18n gate is clean (Article VIII) |
| TC03 | ADR verdict for every entry in `decisions.md`, D1 through D10 | `forge check-adrs` green |
