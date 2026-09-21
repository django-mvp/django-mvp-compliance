# Implementation Plan: Legal documents kept as versioned records

**Branch**: `feat/001-legal-documents-kept` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-legal-documents-kept/spec.md`

## Summary

Two models. `Document` is a name and nothing else — no wording lives on it. `Version` belongs to one
document, carries the Markdown its author wrote, a package-assigned number, and a state that is one
of draft, current or superseded.

Publishing is a method on `Version`. It renders the Markdown through a sanitiser, stores the
resulting HTML on the row, supersedes whatever was current, and makes itself current, all inside one
transaction. From that moment the row's wording is fixed: `save()`, `update()`, `bulk_update()` and
both delete routes refuse to touch a published version's content, and the refusal lives on the
manager rather than in any caller, so a shell session and a shipped migration hit the same wall.

"At most one version in force" is a partial unique index rather than application logic, so two
publishes racing each other cannot both win. Reading is the related manager with a custom queryset:
the current version, one version by its number, and the published history in order.

No admin, no forms, no views, no URLs — `decisions.md` D5, and `tests/test_app.py` grows an assertion
that keeps it true.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.14)

**Primary Dependencies**: Django 5.2 and 6.0, django-mvp 0.23.0.

**Runtime dependencies added here**: `markdown` and `nh3`. Article VII justification in
`research.md` R4 and in Complexity Tracking below.

**Storage**: two tables, `mvp_compliance_document` and `mvp_compliance_version`, one migration after
the S5 consolidation.

**Testing**: pytest with pytest-django, `tests/settings.py`, an in-memory SQLite database.
`factory_boy` factories per Article X.

**Target Platform**: a Django project that has installed django-mvp.

**Project Type**: installable Django application. This feature is its data layer and has no surface
a person can see.

**Constraints**: Article XII (a published version is immutable, enforced in the model layer), Article
XIII (the stored HTML is the evidence and is never re-rendered), Article XV (nothing here holds
personal data — a version names no person, and acceptances are R3).

**Scale/Scope**: two models, one renderer, two exceptions, five user stories, 22 functional
requirements.

## Constitution Check

Read before planning and re-checked after the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every requirement here is an invariant, and an invariant is the easiest thing there is to write a failing test for first. SC-003 makes one test per mutation route mandatory | Pass |
| II Simplicity | Two models, one renderer class, two exception classes, one setting. No registry, no state machine library, no abstract base | Pass |
| III Anti-Abstraction | `MarkdownRenderer` is one concrete class, not a base class with one subclass. The state field is three string values, not a polymorphic hierarchy | Pass |
| IV Integration-First | The contract is the public Python surface the package's later features consume, and every acceptance scenario exercises it the way they will | Pass |
| V Security & data-safety | Authored Markdown is passed through an explicit allow list before storage, so what is served can never carry script. Nothing is interpolated by hand | Pass |
| VI Documentation | README gains the model surface and the one setting; CHANGELOG gains an Added entry. Docstrings on both models, the renderer and both exceptions | Pass |
| VII Dependency discipline | Two runtime dependencies added, each with a stated justification. `deptry` sees both imported | Pass, with Complexity Tracking |
| VIII Internationalization | Every `verbose_name`, `help_text` and exception message wrapped with `gettext_lazy`. A `locale/en/LC_MESSAGES/django.po` catalog ships | Pass |
| IX Data-model conventions | Every field's indexing decision is stated in Data model below. `verbose_name` and `help_text` on every field. Migrations consolidated at S5 | Pass |
| X Test structure & fixtures | `tests/test_models.py`, `tests/test_rendering.py`, `tests/test_exceptions.py` mirror the source. One factory per model in `tests/factories.py`, tested by `tests/test_factories.py`. Classes group by subject | Pass |
| XI Cohesion (Python) | Rendering is a class. Publishing is a model method. Retrieval is queryset methods. No module-level function takes a model instance | Pass |
| XII Published version immutable, record append-only | The feature. Enforced on `save()`, `update()`, `bulk_update()` and both delete routes, with `use_in_migrations` so the historical model inherits it | Pass |
| XIII Rendered output is the evidence | HTML is produced once at publication and stored. Nothing in this feature renders at read time, and no code path re-renders a published version | Pass |
| XIV Mechanics, never compliance | Nothing here names a regulation. The words used are *document*, *version*, *draft*, *published*, *current*, *superseded* | Pass |
| XV Personal data minimal | This feature stores none. A version records no author and no timestamp attributable to a person | Pass |
| XVI Compatibility | Pre-1.0, and every model field added here is new rather than a change of shape, so the migration carries nothing forward | Pass |

## Project Structure

### Documentation (this feature)

```text
specs/001-legal-documents-kept/
├── spec.md              # merged to main at the spec gate
├── decisions.md         # merged with it; appended to here
├── plan.md              # this file
├── research.md          # what had to be settled first
├── tasks.md             # the task graph
├── progress.md          # run narrative
└── feature-state.json   # the ledger
```

No `contracts/`: the contract is a Python API and the test suite states it. The data model is small
enough to live in this file rather than in a `data-model.md` beside it.

### Source code

```text
mvp_compliance/
├── apps.py                      # unchanged
├── exceptions.py                # PublishedVersionError, PublishError
├── models.py                    # Document, Version, their querysets and managers
├── rendering.py                 # MarkdownRenderer, and the resolver for the setting
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py          # one file after the S5 consolidation
└── locale/en/LC_MESSAGES/
    └── django.po                # base catalog

tests/
├── conftest.py                  # document / draft / published_version fixtures
├── factories.py                 # DocumentFactory, VersionFactory
├── test_factories.py
├── test_models.py               # TestDocument, TestVersion, TestPublishing,
│                                # TestImmutability, TestRetrieval
├── test_rendering.py
├── test_exceptions.py
├── test_migrations.py           # no shipped migration writes to a published version
└── test_app.py                  # extended: no admin, no forms, no views, no URLs
```

`tests/test_migrations.py` and `tests/test_app.py` have no source module to mirror; both go in
`[tool.forge.conformance] non-mirror-paths`, which already declares `tests/test_app.py`.

## Design

### Data model

**`Document`**

| Field | Type | Index | Why |
|---|---|---|---|
| `name` | `CharField(max_length=100, unique=True)` | unique, so indexed | The identity a host project and every later feature look a document up by. Uniqueness is what makes "three documents with distinct names" (US-1 scenario 1) mean anything |

No other field. FR-002 is that a document holds no wording, and `tests/test_models.py` asserts the
field set rather than trusting the class to stay that way. No slug: R2 owns addresses, and adding one
later is an additive migration.

**`Version`**

| Field | Type | Index | Why |
|---|---|---|---|
| `document` | `ForeignKey(Document, on_delete=PROTECT, related_name="versions")` | FK index | Every retrieval filters by it. `PROTECT` is what closes the cascade hole — see `research.md` R3 and D8 |
| `number` | `PositiveIntegerField(editable=False)` | composite unique with `document` | FR-003: order is the package's, never the author's. Assigned as `max+1` within the document |
| `status` | `CharField(max_length=10, choices=Status)` | partial unique with `document` where current | FR-004, FR-006. Three values: `draft`, `current`, `superseded` |
| `markdown` | `TextField` | none — no query path, and indexing a body column costs writes for nothing | FR-002: the wording, and the only thing an author writes |
| `html` | `TextField(blank=True)` | none, same reason | FR-015: produced once at publication. Empty on a draft, which is FR-019 |
| `published_at` | `DateTimeField(null=True, blank=True, editable=False)` | none in this feature; R10 may need one and will add it with its query | The moment publication happened. Null on a draft |

**Meta**

- `ordering = ["document", "number"]` — US-1 scenario 2 asks for the order they were added, and the
  number is that order.
- `constraints`:
  - `UniqueConstraint(fields=["document", "number"], name="unique_version_number_per_document")` —
    the numbering cannot collide, including under a race.
  - `UniqueConstraint(fields=["document"], condition=Q(status="current"), name="one_current_version_per_document")` —
    FR-007, enforced by the database rather than by the code that publishes, on every backend that
    supports a partial index. MySQL and MariaDB do not, and Django omits it there rather than
    failing — see `research.md` R1 and D11.
  - `CheckConstraint` tying the three fields that must agree: a draft has no `published_at` and empty
    `html`; a published version has both. This is the one immutability-adjacent rule a check
    constraint *can* express, because it compares columns within the row.

`Status` is a `models.TextChoices` on `Version`. A published version is one whose status is not
`DRAFT`; that test lives on the model as `is_published`, not repeated at each call site.

### Publishing

`Version.publish()`, one method, inside `transaction.atomic()`:

1. Refuse when `self.status != DRAFT` — FR-010, `PublishError`, and nothing about the document moves.
2. Render `self.markdown` through the configured renderer. Refuse when the result is empty once
   whitespace is stripped — FR-018 and D7, `PublishError`, before anything is written.
3. `Document.objects.select_for_update().get(pk=...)` — take the row lock so the ordinary path
   serialises rather than racing.
4. Move the document's current version, if there is one, to `superseded`.
5. Set `html`, `published_at = timezone.now()`, `status = CURRENT`, and save.

An `IntegrityError` from the partial unique index is translated into `PublishError`, because a caller
should not have to know which index it hit.

Both mechanisms are load-bearing, and which one carries depends on the backend the host project
runs. On SQLite and PostgreSQL the index is the guarantee and the lock is ergonomics. On MySQL and
MariaDB the index is not created at all, and the lock is the whole of it. `research.md` R1 has the
table and the Django source lines; D11 records what that means for a host project.

There is no `unpublish`, no `revert` and no `make_current`. FR-009 is satisfied by the absence, and
`tests/test_models.py` asserts the absence by name so a later convenience cannot be added quietly.

### Immutability

`PUBLISHED_FROZEN_FIELDS = ("document", "number", "markdown", "html", "published_at")`. Everything
except `status`, because FR-013 says a change of standing is the only change a published version ever
undergoes.

Four routes, all refusing with `PublishedVersionError`:

- **`Version.save()`** — when the row already exists and the stored row is published, re-read the
  stored values and raise if any frozen field differs. Reading the stored row rather than trusting an
  in-memory snapshot is what makes the check survive `refresh_from_db`, deferred loading and an
  instance built by a third party.
- **`VersionQuerySet.update()`** — raise when the queryset matches any published row and the update
  names a frozen field. An update naming only `status` is how `publish()` supersedes, so it passes.
  The comparison is against each field's `name` *and* its `attname`, because a foreign key arrives
  as `document_id`.
- **`Version.delete()` and `VersionQuerySet.delete()`** — refuse for published rows outright
  (FR-014).

`bulk_update()` gets no override. It calls `self.filter(pk__in=pks).update(**update_kwargs)`
internally (`django/db/models/query.py:920-923`), so the `update()` guard already catches it. It
still has a test, because that is a claim about Django's internals rather than about this package.

`VersionManager.use_in_migrations = True`, so a historical model in a shipped migration gets this
manager and its queryset. `tests/test_migrations.py` covers the residue that leaves — a shipped data
migration calling `save()` on a historical instance — by asserting no shipped migration writes to a
published version at all.

Document deletion needs no override: `PROTECT` on the foreign key means the collector refuses on
every route, including a queryset delete and a cascade from somewhere else.

### Rendering

`mvp_compliance/rendering.py`:

```text
class MarkdownRenderer:
    extensions          # ["extra", "sane_lists", "smarty"]
    allowed_tags        # explicit set: headings, p, lists, em/strong, a, blockquote,
                        # code/pre, hr, table family. No script, no style, no iframe,
                        # no form, no object, no embed.
    allowed_attributes  # {"a": {"href", "title"}, "th": {"colspan", "rowspan"}, ...}
    allowed_url_schemes # {"http", "https", "mailto"}

    def render(self, source: str) -> str      # markdown -> nh3.clean -> str
```

Configuration is one setting, `MVP_COMPLIANCE_RENDERER`, a dotted path resolved with
`import_string` and defaulting to this class. A host project that wants a different allow list
subclasses and points the setting at the subclass, which is what Article XI says a class is for. The
resolver is a module-level function, which Article XI permits as a thin wrapper that returns the
class.

`render()` is deliberately not called anywhere except `publish()`. Article XIII is the reason, and
`tests/test_models.py` asserts a published version's `html` survives a renderer swap.

### Retrieval

`VersionQuerySet` gains `published()`, `drafts()` and `current()`; the related manager is where every
consumer asks:

- the version in force — `document.current`, a property returning the current `Version` or `None`.
  `None` is a normal answer (FR-008, US-5 scenario 4), never an exception.
- one named version — `document.versions.get(number=n)`, the plain Django idiom, no wrapper.
- the published history in order — `document.versions.published()`, drafts absent (FR-022).

### Exceptions

`mvp_compliance/exceptions.py`, two classes, both subclassing `Exception`:

- `PublishedVersionError` — an attempt to change or delete a published version.
- `PublishError` — publication refused: already published, or empty output.

Neither subclasses `ValidationError`. A `ValidationError` is a message for a form, and there is no
form in this feature; these are invariant breaches, and swallowing one into a form error would be
exactly the silent discard FR-012 forbids. Issue #5 builds the forms and will decide how to present
them.

## Phases

**Foundational** (sequential, before any story): add `markdown` and `nh3` to the runtime dependencies
and update the lock file; create `mvp_compliance/migrations/__init__.py`; add `tests/factories.py`
scaffolding; declare the new non-mirror test path.

Then the stories in priority order, dispatched one at a time into a single worktree. Each one builds
on the last, and they are not independent: they are five layers of one model module, which is why
they are sequential rather than parallel.

| Story | Priority | What it adds |
|---|---|---|
| US-1 | P1 | `Document`, `Version`, the document foreign key, `number` assignment, `markdown`, the first migration, factories, and the assertion that a document holds no wording |
| US-2 | P1 | `status`, `published_at`, both unique constraints, `publish()`, `PublishError`, and the absence of every reverse operation |
| US-3 | P1 | `PublishedVersionError` and all four refusal routes, `use_in_migrations`, `PROTECT`, one test per route per SC-003 |
| US-4 | P2 | `html`, `MarkdownRenderer`, the `MVP_COMPLIANCE_RENDERER` setting, rendering inside `publish()`, the empty-output refusal, the renderer-swap test |
| US-5 | P2 | `published()`, `drafts()`, `current()`, `Document.current`, and the retrieval tests over a three-version history |

**Convergence** (S5, Forge): squash the five stories' migrations into `0001_initial.py`, run the
cleanup pass over the feature diff, and decide the ADR verdict for each entry in `decisions.md`.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| Two runtime dependencies added (`markdown`, `nh3`) | Article XIII requires rendering through a sanitiser with an explicit allow list, and neither Django nor the standard library renders Markdown or sanitises HTML | Writing either by hand. A hand-rolled sanitiser is the single worst thing to hand-roll: its failure mode is stored script served to every visitor, and it is stored rather than reflected, so one mistake is permanent |
| `nh3` rather than the more familiar `bleach` | `bleach` was deprecated by its own maintainers in 2023 and its documentation points at `nh3` | Adding a dependency its authors have stopped maintaining, to a package whose reason for existing is that records outlive the code |
| One setting, `MVP_COMPLIANCE_RENDERER` | US-4 scenario 3 requires a markup rendering configuration that can change, so one has to exist for the scenario to be testable | A setting per knob — extensions, tags, attributes, schemes — which is four settings for the same reach, and none of them composes with the others |
| `PROTECT` makes a document holding drafts undeletable, one step stricter than D6 | The alternative is `CASCADE` plus overrides on two delete routes, and a missed route destroys published versions | See D8. The stricter rule fails safe; the looser one fails by deleting evidence |
