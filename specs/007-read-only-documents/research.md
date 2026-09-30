# Research — 007 Documents that are read but never agreed to

The evidence behind the choices in [plan.md](./plan.md). Citations are to the Django the project
resolves (6.1.1 in `.venv`) and to this repository on `origin/main` at `4e7973f`.

## Every route that answers "still has to accept"

`grep -rn outstanding mvp_compliance/` finds two public routes:

- `DocumentQuerySet.outstanding_for()` (`models.py:76`) with its manager forwarder (`models.py:108`).
- `Document.is_outstanding_for()` (`models.py:185`), which is
  `Document.objects.outstanding_for(user).filter(pk=self.pk).exists()`.

The second is built on the first, so a filter added to the first covers both (FR-003 "for many
documents or for one"). Nothing else in the package, including `records.produce()`, asks the
question.

## Every route that creates an acceptance

- `AcceptanceManager.record()` (`models.py:782`), the package's documented route, which ends in
  `self.get_or_create(...)`.
- Any ORM route a project can call on `Acceptance.objects`: `create()` and `get_or_create()`, both of
  which end in `Model.save()`, and `bulk_create()`, which does not call `save()`.
- `seed_demo` calls `record()` only (`demo/management/commands/seed_demo.py:214`, `:221`).

**`get_or_create()` returns an existing row without saving anything.**
`django/db/models/query.py:1070`: `return self.get(**kwargs), False` runs first, and `create()` runs
only on `DoesNotExist` (`:1077`). A refusal placed only in `Acceptance.save()` would never run for a
user who accepted a document before it became a notice: `record()` would return their old record.
Hence the refusal in `record()` comes before `get_or_create()`.

**`bulk_create()` bypasses `save()`.** It inserts the objects directly (`query.py:833`). It is the
only row-creating route a `save()` check does not cover.

## A version read through its document's related manager already knows its document

`django/db/models/fields/related_descriptors.py:784`: the reverse manager sets
`queryset._known_related_objects = {self.field: {rel_obj_id: self.instance}}`, so every version it
returns has `document` set to the instance the manager came from, without a query.
`DocumentView.get_version()` reads `self.object.versions.published().with_replaced_at()`
(`views.py:79`), so `version.document.kind` in the subtitle mixin costs nothing.

## The migration

`AddField` with a non-callable `default` writes that default into every existing row as part of the
schema change. No data migration is needed, and none is allowed (`tests/test_migrations.py`,
`TestMigrationOperations`, ADR 0004). The existing `TestPublisherMigration` shows the pattern for a
test that builds rows at an earlier migration state and reads them back after migrating forward.

## The admin form

`DocumentAdmin` (`admin.py:20`) declares neither `fields` nor `fieldsets`, so Django's `ModelAdmin`
builds the form from every editable field. A new `choices` field appears on the add and change
forms as a select with its default preselected, with no admin change.
