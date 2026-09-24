# Progress — 005 Announcing that a version was published

The running log of this feature's implementation run. The ledger (`feature-state.json`) is the
machine record; this is the readable one.

---

## 2026-09-24 — S3 PLAN

Picked off the feature queue as the one feature ready to build in this repo, with no feature
delivered since the specification landed, so there was nothing to re-read it against. Branch
`005-announcing-a-version-published` cut from `origin/main` at `61b23e8`, which carries the
specification merged in #43. Verify green on that commit: lint, typecheck, tests, build.

Plan, research and tasks written. Three stories, run in sequence: US-2 (the publisher) first,
because the signal carries it and the email shows it.

## 2026-09-24T13:20Z · Implementer US-2 · T001, T002, T003

Did: `TestPublisher` in `tests/test_models.py` (recording, nobody named, draft empty, unsaved user, draft-with-publisher refused by the database, frozen through `save()` and `update()` for `publisher`, `publisher_id`, `publisher_subject`). Then `Version.publisher` / `publisher_subject`, both frozen, the widened draft branch of the check constraint, `publish(publisher=None)` through `Acceptance.subject_of()`, refusal messages now say "wording and publisher", migration `0005_version_publisher`. `en` catalog regenerated so `TestUserFacingStrings` stays green between tasks.
Verified: before the model change `TestPublisher` failed with `TypeError: publish() got an unexpected keyword argument 'publisher'`; after, `pytest tests/test_models.py::TestPublisher` 10 passed; `tests/test_models.py tests/test_admin.py` green; `makemigrations --check` clean; ruff clean.
Next: T004 account removal.
Watch: never set `Meta.base_manager_name` (comment on the field).

## 2026-09-24T13:30Z · Implementer US-2 · T004, T005

Did: account-removal test in `TestPublisher`; `TestPublisherDisplay` and `Version.publisher_display` (the four rows of the plan's table). Catalog regenerated.
Verified: `pytest tests/test_models.py::TestPublisher tests/test_models.py::TestPublisherDisplay` 17 passed. Display tests failed first with `AttributeError: no attribute 'publisher_display'`. Probe for T004: with `Meta.base_manager_name = "objects"` temporarily set, the removal test failed with `PublishedVersionError` raised from `VersionQuerySet.update()` inside `deletion.py`'s collector; setting reverted.
Next: T006 migration test.
Watch: none.

## 2026-09-24T13:40Z · Implementer US-2 · T006

Did: `TestPublisherMigration` — builds a published version on the 0004 state through the historical model, migrates to 0005, checks wording, html, standing and published_at unchanged, `publisher` null, `publisher_subject` empty; restores the latest state in `finally`.
Verified: `pytest tests/test_migrations.py` 2 passed.
Next: T007 admin publish test.
Watch: test uses `transaction=True`.

## 2026-09-24T13:50Z · Implementer US-2 · T007, T008

Did: `TestPublisherInTheAdmin` publish test; `publish_view` now calls `version.publish(publisher=request.user)`. No success message (US-1).
Verified: the test failed first with `assert None == <User: person0>`; `pytest tests/test_admin.py::TestPublisherInTheAdmin tests/test_admin.py::TestPublish` green.
Next: T009/T010 display columns.
Watch: none.

## 2026-09-24T14:05Z · Implementer US-2 · T009, T010

Did: `TestPublisherInTheAdmin` display tests (version page beside Published at, removed account, draft empty value, both lists, query counts at 2 vs 10 rows for both lists); `published_by` on `VersionAdmin` (readonly_fields, list_display, list_select_related) and `DocumentAdmin` (list_display, select_related inside the prefetch). Catalog regenerated.
Verified: five display tests failed first (no "Published by"); `pytest tests/test_admin.py` 98 passed after the catalog step. Probe: removing both `select_related("publisher")` calls made both query-count tests fail; restored.
Next: T011 docs.
Watch: none.

## 2026-09-24T14:20Z · Implementer US-2 · T011

Did: `CONTEXT.md` Publisher; `docs/models.md` Publishing (argument, two fields, the `publisher_display` table, account removal) and Immutability list; `docs/authoring.md` Publishing, the admin's read-only page and the list of fields the package owns; `CHANGELOG.md` `[Unreleased]` entry naming the new personal data. `en` catalog regenerated; no new strings beyond T010's.
Verified: `makemessages` a second time leaves the catalog unchanged; full verify run next.
Next: full verify and report.
Watch: `records.py` untouched (D4).

## 2026-09-24T14:35Z · Implementer US-1 · T012

Did: `TestVersionPublished` with an `announcements` fixture that connects a recording receiver and disconnects it on teardown; three tests (once with version, publisher, replaced; nobody named; replaced is superseded on the instance).
Verified: `pytest tests/test_models.py::TestVersionPublished -x` errored first with `ModuleNotFoundError: mvp_compliance.signals`.
Next: T013.
Watch: this commit is red by design.

## 2026-09-24T14:40Z · Implementer US-1 · T013

Did: `mvp_compliance/signals.py` with `version_published`; `publish()` sets the superseded version's status on the instance and registers `send_robust` on commit after `save()`, inside the atomic block.
Verified: `pytest tests/test_models.py::TestVersionPublished` 3 passed; ruff check and format clean.
Next: T014 refusal tests.
Watch: none.

## 2026-09-24T14:55Z · Implementer US-1 · T014, T015, T016

Did: `TestVersionPublished` gains the three-refusals test (each refusal, then a control publication that does announce), rollback and commit-timing tests, the receiver-sees-current test, a raising receiver (logged on `django.dispatch`, later receiver still runs, publication stands), a receiver that publishes another version, and two documents in one transaction. A `connect` fixture disconnects every receiver a test connects.
Verified: `pytest tests/test_models.py::TestVersionPublished` 10 passed (these pass on T013's code by design). Mutation probes, each restored: registering before the refusals failed 8; sending directly rather than on commit failed 5; `send` instead of `send_robust` failed the raising-receiver test; dropping the superseded status on the instance failed the replaced test.
Next: T017 admin test.
Watch: none.
