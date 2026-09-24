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
