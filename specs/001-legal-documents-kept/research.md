# Research — 001 Legal documents kept as versioned records

What had to be settled before the plan could be written. Each item names the question, what was
found, and what the plan does about it.

## R1 — How "at most one version in force" survives two publishes at once

**Question**: FR-007 requires exactly one current version per document even when two publishes race.
Application-level code that reads the current version, supersedes it and then promotes a new one is
a read-modify-write, and two of them interleave.

**Found**: Django supports partial unique indexes through `UniqueConstraint(condition=...)` on
SQLite and PostgreSQL, and **not** on MySQL or MariaDB. `supports_partial_indexes` defaults to
`True` (`django/db/backends/base/features.py:303`) and MySQL's backend sets it to `False`
(`django/db/backends/mysql/features.py:45`, comment: "Neither MySQL nor MariaDB support partial
indexes"). On a backend without support, Django does not raise: it emits system check `models.W036`
and omits the constraint (`django/db/models/constraints.py:392-405`). A constraint that is silently
absent is worse than one that fails loudly, so this is stated rather than assumed.

The row lock is the other half. `select_for_update()` takes real row locks on PostgreSQL and MySQL.
SQLite ignores it, and does not need it: it serialises writers at the database level.

So the two mechanisms cover the three backends between them, and neither covers all three alone:

| Backend | Partial unique index | `select_for_update()` |
|---|---|---|
| SQLite | enforced | ignored — writers already serialise |
| PostgreSQL | enforced | real row lock |
| MySQL / MariaDB | **silently omitted** | real row lock |

**Plan**: `publish()` takes the row lock inside a transaction *and* the partial unique constraint is
declared. On SQLite and PostgreSQL the constraint is the backstop and the lock is ergonomics; on
MySQL the lock is the whole of it. Tested on SQLite, which is what this repository's CI runs
(`tests/settings.py` uses an in-memory SQLite database and no workflow starts a database service) —
a direct attempt to write a second current row must raise `IntegrityError`, and two publishes must
leave exactly one current version. See D11 for what a MySQL-backed host project is and is not
promised.

## R2 — Where immutability can actually be enforced

**Question**: FR-011 says the rule lives with the data rather than with any one caller, and names
shell sessions, management commands and shipped data migrations as routes that must fail.

**Found**: Django offers no declarative "this row is now read-only". A `CheckConstraint` compares
columns within a row and cannot see the previous value, so it cannot express "unchanged". Database
triggers can, but they are per-backend SQL and this package supports three backends through the
host project's choice, so shipping trigger DDL in a migration means maintaining three dialects and
a fourth path for any backend a host project brings.

What Django does offer covers every route this package can reach:

- `Model.save()` is the single funnel for instance writes, including from a shell and from a
  management command.
- `QuerySet.update()` and `QuerySet.delete()` are the bulk routes, and both can be overridden on a
  custom `QuerySet` and reached through a `Manager`.
- `Manager.use_in_migrations = True` makes the historical model inside a migration use this
  package's manager, so a shipped data migration calling `.update()` hits the same refusal.

The residue is a shipped data migration that calls `save()` on a historical instance: historical
models are rebuilt from migration state and do not carry custom `save()`. That is a route this
package writes rather than one it offers to anybody else, so it is closed by not writing one, and a
test asserts no shipped migration writes to a published version.

`bulk_update()` needs no guard of its own: it builds `Case`/`When` expressions and then calls
`self.filter(pk__in=pks).update(**update_kwargs)` on a queryset of the same class
(`django/db/models/query.py:920-923`), so an override on `update()` already intercepts it. One
detail follows from the same lines — `update_kwargs` is keyed on `field.attname`, so a guard that
compares against field *names* alone misses `document_id`. The guard compares against both.

**Plan**: enforcement on `save()` and on the queryset's `update()` and `delete()`, with
`use_in_migrations = True` on the manager. `bulk_update()` is covered transitively and is tested
anyway, because "covered transitively" is a claim about Django's internals and a test is what keeps
it true. One test per route, per SC-003, and the residue named in `decisions.md` rather than left
unstated.

## R3 — Deleting a document without opening a hole under the versions

**Question**: FR-014 forbids deleting a published version and forbids deleting a document that holds
one. `decisions.md` D6 also says a document created by mistake and never published can still be
deleted.

**Found**: `on_delete=CASCADE` would take published versions with the document, and `QuerySet.delete()`
never calls `Model.delete()`, so an override on the model alone leaves the bulk route open.
`on_delete=PROTECT` is enforced by Django's deletion collector on every route — instance delete,
queryset delete, cascade from a third model, and the historical model inside a migration, since
`on_delete` is part of the field rather than of the model class.

**Plan**: `PROTECT` on the version's document foreign key. A document holding any version cannot be
deleted; discarding its drafts first (FR-005) returns it to the freshly-created state and it deletes
normally. This is stricter than D6 by one step and is recorded as D8 rather than assumed.

## R4 — Markdown and the allow list

**Question**: Article XIII requires rendering through a sanitiser with an explicit allow list, and
the package declares no Markdown library yet.

**Found**:

- **Python-Markdown** (`markdown`) is the long-standing default in Django projects, ships the
  `extra` extension set, and is actively maintained.
- **`bleach`** was the usual sanitiser and was deprecated by its maintainers in 2023. Its own
  documentation points users at **`nh3`**, Python bindings for the Rust `ammonia` library, which is
  maintained, fast, and takes an explicit tag and attribute allow list.

**Plan**: `markdown` for rendering and `nh3` for sanitising, both declared as runtime dependencies
with the justification Article VII requires. The allow list is explicit class configuration on a
single renderer class, not a module-level constant, so a host project overrides it by subclassing —
which is what Article XI says a class is for.

## R5 — How a "markup rendering configuration change" is expressed

**Question**: US-4 scenario 3 requires the stored output to survive a change to the markup rendering
configuration, so such a configuration has to exist and be changeable for the scenario to be
testable at all.

**Found**: Django's own idiom for a swappable implementation is one setting naming a dotted path,
resolved through `django.utils.module_loading.import_string`. That is one setting rather than one
per knob, and it is the same shape a host project already knows from `DEFAULT_FILE_STORAGE`,
`AUTH_PASSWORD_VALIDATORS` and their neighbours.

**Plan**: one setting, `MVP_COMPLIANCE_RENDERER`, naming the renderer class. The extension list and
the allow list are class attributes on it, so overriding either means subclassing and pointing the
setting at the subclass. The test for US-4 scenario 3 swaps the renderer with `override_settings`
and asserts the stored HTML is unchanged.

## R6 — Prior art, and what it does differently

From `docs/brainstorm.md`, re-checked against the two packages' current source:

- **`django-termsandconditions`** is already multi-document and already database-backed, so neither
  of those is the gap. Its published rows stay mutable: editing `TermsAndConditions.text` silently
  rewrites what a user is recorded as having accepted. It also carries an author-supplied
  `version_number` while computing the active version from a separate date field, so the number
  orders nothing — the two-sources-of-truth defect D2 exists to avoid.
- **`django-tos`** is genuinely single-document.

Neither stores the rendered output, so both re-render at request time, which is what Article XIII
prohibits.

**Plan**: nothing is borrowed. The observations are already carried by `decisions.md` D2 and by
Articles XII and XIII; this entry records that the source was checked rather than remembered.
