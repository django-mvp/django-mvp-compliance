# Implementation Plan: The record of who accepted which version

**Branch**: `003-record-who-accepted` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-record-who-accepted/spec.md`

## Summary

One model. `Acceptance` names a person, points at a published `Version`, and carries the moment it
happened. Nothing else, unless a project asks for more.

It is written through one manager method and never through anything else. `record()` refuses a draft
version, and uses `get_or_create()` over a unique constraint so that a repeat — including a repeat
arriving at the same instant — leaves the one record that already exists. From that moment the row
is finished: `save()`, `update()`, `bulk_update()` and both delete routes refuse, and the refusal
lives on the manager, so a shell session and a shipped migration hit the same wall FS-001 built.

The person is named twice, deliberately. A foreign key to the host project's user model carries the
ordinary relationship, and a `subject` column holds that account's primary key as text, written when
the record is. Under the package's default an account's removal clears the foreign key and leaves
the record standing, and `subject` is what still says whose it is and what still gathers a person's
records into a set. Which of the two happens is a setting, read at deletion time through a callable
`on_delete`.

Reading is one question asked two ways: `Document.objects.outstanding_for(user)` for every document
whose version in force this person has not accepted, and `document.is_outstanding_for(user)` for one
of them, narrowing the same queryset rather than restating the rule. Both cost a fixed number of
lookups, which R4's flow needs because it asks on an ordinary page request.

No admin, no forms, no views, no URLs — the spec's own scope, and `tests/test_app.py` already holds
an assertion that keeps it true.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.14)

**Primary Dependencies**: Django 5.2 and 6.0, django-mvp 0.23.0. **No new runtime dependency** — this
feature adds a model, a manager and two settings, all of them Django.

**Storage**: one new table, `mvp_compliance_acceptance`, one migration (`0002_*`) after the S5
consolidation. `0001_initial.py` is on main and is not touched.

**Testing**: pytest with pytest-django, `tests/settings.py`, an in-memory SQLite database.
`factory_boy` factories per Article X, and `django_assert_num_queries` for the query bound in SC-005.

**Target Platform**: a Django project that has installed django-mvp.

**Project Type**: installable Django application. This feature has no surface a person can see.

**Constraints**: Article XII (an acceptance is never edited and never deleted, enforced in the model
layer), Article XV (the record holds three facts; anything beyond them is off unless the project asks
and is justified where it is defined), Article XVI (a migration carries existing records forward).

**Scale/Scope**: one model, one manager, one queryset on each of two models, two exceptions, two
settings, five user stories, 18 functional requirements.

## Constitution Check

Read before planning and re-checked after the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every requirement here is an invariant, and SC-001 makes one test per refused route mandatory. The failing test comes first on every task | Pass |
| II Simplicity | One model, one manager method that writes, two queryset methods that read, two settings. No service layer, no registry, no signal | Pass |
| III Anti-Abstraction | No settings-object wrapper for two settings, no base class for one model, no abstraction over "the person" beyond the column that holds them | Pass |
| IV Integration-First | The contract is the public Python surface R4, R5, R9, R10 and issues #21/#22 consume, and every acceptance scenario exercises it the way they will | Pass |
| V Security & data-safety | Nothing is rendered here. The one place external input reaches the model is the client address, and R6 records why the package reads `REMOTE_ADDR` and refuses to parse a header the client controls | Pass |
| VI Documentation | `docs/models.md` gains the acceptance surface, README gains both settings, CHANGELOG gains an Added entry naming the personal data the optional one holds (Article XV). Docstrings on the model, the manager, the queryset methods and both exceptions | Pass |
| VII Dependency discipline | No new runtime dependency | Pass |
| VIII Internationalization | Every `verbose_name`, `help_text` and exception message wrapped with `gettext_lazy`; the shipped `en` catalog regenerated | Pass |
| IX Data-model conventions | Every field's indexing decision is stated in Data model below, with the one composite index that serves both query paths. `verbose_name` and `help_text` on every field. The branch's migrations consolidated at S5 | Pass |
| X Test structure & fixtures | `tests/test_models.py` and `tests/test_exceptions.py` already mirror the source and grow classes rather than files. One factory per model, including a `UserFactory` for the auth user the tests need | Pass |
| XI Cohesion (Python) | Writing is a manager method, reading is queryset methods on the model that answers, identity is a `staticmethod` on the model that holds it. The one module-level function is the `on_delete` callable, which is the shape Django dictates for that argument | Pass |
| XII Published version immutable, record append-only | The feature's second half. Enforced on `save()`, `update()`, `bulk_update()` and both delete routes, with `use_in_migrations` so the historical model inherits it | Pass |
| XIII Rendered output is the evidence | Nothing here renders or re-renders. The record points at the version whose stored output is the evidence, and holds no copy of the wording | Pass |
| XIV Mechanics, never compliance | The words used are *acceptance*, *recorded*, *outstanding*, *published*. No regulation is named, and nothing claims the package makes a site anything | Pass |
| XV Personal data minimal | The whole of US-5, and the reason `subject` gets a justification where it is defined. The optional client address defaults to off and its CHANGELOG entry names it in plain language | Pass |
| XVI Compatibility | Pre-1.0. One new table; no existing model changes shape, so no record is carried forward or at risk | Pass |

## Project Structure

### Documentation (this feature)

```text
specs/003-record-who-accepted/
├── spec.md              # on main, merged in #23
├── decisions.md         # on main; appended to, never restarted
├── plan.md              # this file
├── research.md          # the six questions the design rests on
├── tasks.md             # the task list feature-state.json tracks
├── progress.md          # the running log
└── feature-state.json   # the ledger
```

No `data-model.md` and no `contracts/`: the data model is one table and lives in the Design section
below, and the contract is a Python surface with no wire format to specify.

### Source code

```text
mvp_compliance/
├── models.py            # + Acceptance, AcceptanceQuerySet, AcceptanceManager,
│                        #   DocumentQuerySet, keep_or_remove_acceptances
├── exceptions.py        # + RecordedAcceptanceError, RecordError
├── migrations/
│   └── 0002_acceptance.py
└── locale/en/LC_MESSAGES/django.po   # regenerated

tests/
├── factories.py         # + UserFactory, AcceptanceFactory
├── conftest.py          # + user, acceptance fixtures
├── test_models.py       # + TestAcceptance, TestRecording, TestAcceptanceImmutability,
│                        #   TestOutstanding, TestAccountRemoval, TestOptionalEvidence
├── test_exceptions.py   # + the two new exception classes
└── test_factories.py    # + the two new factories

docs/models.md           # + the acceptance surface
README.md                # + both settings
CHANGELOG.md             # + the Added entry
```

**Structure Decision**: `models.py` stays one module. Article X ties one source module to one test
module, and splitting the package into a `models/` package to separate two small model groups would
buy nothing but a mirrored test directory. The grouping inside the module is by class, which is where
Article XI puts it.

## Design

### Data model

**`Acceptance`**

| Field | Type | Index | Why |
|---|---|---|---|
| `user` | `ForeignKey(settings.AUTH_USER_MODEL, on_delete=keep_or_remove_acceptances, null=True, blank=True, related_name="compliance_acceptances")` | FK index | The ordinary relationship, and what a signed-in request already has in its hand. Null only ever means "the account has since been removed" (FR-013), never "we did not know" — `record()` refuses a user without a primary key. `related_name` is prefixed because this accessor lands on the host project's own user model |
| `subject` | `CharField(max_length=255, editable=False)` | composite unique with `version`, which indexes it as a prefix | The account's primary key as text, written when the record is. It is what a surviving record still says about whose it is (FR-014), and what gathers one person's records into a set for issues #21 and #22. Article XV justification: it is a pseudonymous identifier and it is the least that can be held and still answer that question — see `research.md` R5 for the two alternatives and why each is worse |
| `version` | `ForeignKey(Version, on_delete=PROTECT, related_name="acceptances")` | FK index | FR-002: the record points at a version, never at a document. `PROTECT` costs nothing — a published version already cannot be deleted (FS-001 FR-014) — and it closes the same hole for a draft that somebody accepted, which cannot happen because FR-003 refuses drafts, and would be silent if it ever did |
| `accepted_at` | `DateTimeField(editable=False, db_index=True)` | indexed | FR-001's third fact, and `Meta.ordering`'s key, so it has an ordering path. Article IX indexes a field with a query path at its definition, because a consumer of a published package cannot add the index later. Set in `record()` rather than `auto_now_add`, so it is a value the model holds rather than a behaviour on write — `auto_now_add` also silently rewrites on every save, which is the opposite of an append-only record |
| `ip_address` | `GenericIPAddressField(null=True, blank=True)` | none — no query path, and it is not something to look a person up by | FR-016's optional additional evidence, empty unless the project turned it on and a request was supplied. Article XV justification: it strengthens the evidence by saying where the agreement came from, it is personal data about somebody who did not ask for it to be kept, and so it is the host project's decision and defaults to off |

**Meta**

- `ordering = ["accepted_at", "id"]` — US-2 scenario 2 asks for the order they happened; `id` breaks
  a tie so the order is total rather than merely usually stable.
- `constraints`:
  - `UniqueConstraint(fields=["subject", "version"], name="one_acceptance_per_person_per_version")` —
    FR-009 and FR-010. Over `subject` rather than `user` so it still holds for records whose account
    is gone, and so it cannot be defeated by the foreign key being cleared.
- `verbose_name = _("acceptance")`, `verbose_name_plural = _("acceptances")`.

`Acceptance.subject_of(user)` is a `staticmethod` returning `str(user.pk)`, and raises `RecordError`
when the user has no primary key. It is the single place the identifier is derived, so writing and
reading cannot disagree about what identifies a person.

### Recording

`Acceptance.objects.record(user, version, request=None)`, the only route that writes:

1. Refuse when `not version.is_published` — FR-003, `RecordError`. A draft has no standing for
   anybody to agree to.
2. Derive the subject from the user, which refuses an anonymous or unsaved user.
3. Read the client address when `MVP_COMPLIANCE_RECORD_IP_ADDRESS` is on and a request was supplied —
   `request.META.get("REMOTE_ADDR")` and nothing else, per `research.md` R6.
4. `get_or_create(subject=..., version=..., defaults={...})`, returning the `Acceptance`.

`get_or_create()` is what makes a repeat succeed and leave one record, including when two attempts
race: it falls through to a `create()` inside `transaction.atomic()` and, on the `IntegrityError` the
unique constraint raises, re-runs the `get` and returns the row the other writer made
(`research.md` R3). The record is not refreshed or updated on that path — FR-017's "turning the
additional evidence on affects only acceptances recorded afterwards" holds for free, because the
second attempt writes nothing.

There is no `record_for_document()`, and there is no way to express an acceptance against a
`Document`: FR-002 is satisfied by the field set, and `tests/test_models.py` asserts the field names
so one cannot be added quietly.

### Immutability

Every field is frozen. Unlike a version, an acceptance has no `status` that may still move, so the
guard is a refusal rather than a comparison (`research.md` R2):

- **`Acceptance.save()`** — refuse when the row already exists in the database. Asked of the database
  rather than of Django's "adding" flag, for the reason FS-001 records: an instance built as
  `Acceptance(pk=...)` has never been fetched and reports itself as being added.
- **`AcceptanceQuerySet.update()`** — refuse whenever the queryset matches anything.
- **`Acceptance.delete()` and `AcceptanceQuerySet.delete()`** — refuse outright (FR-006).

`bulk_update()` gets no override, for the reason FS-001 found: it calls
`self.filter(pk__in=pks).update(**kwargs)` internally, so the `update()` guard already catches it. It
still has its own test, because that is a claim about Django's internals.

`AcceptanceManager.use_in_migrations = True`, so a historical model in a shipped migration inherits
the guard — the route FR-004 names, and the one `tests/test_migrations.py` already watches for
versions.

Both exceptions raise loudly rather than returning or logging, which is FR-005.

### What happens when an account is removed

`keep_or_remove_acceptances(collector, field, sub_objs, using)` is the `on_delete` callable on
`Acceptance.user`. It reads `MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL` (default `True`) at
the moment a delete runs and delegates to Django's own `SET_NULL` or `CASCADE`.

That the setting is read per delete rather than per process is what makes it a setting at all, and
what makes it testable with `override_settings` — `research.md` R1 has the mechanism and the system
check that does not fire.

The configured removal does not collide with FR-006. The collector issues its deletes through
`sql.DeleteQuery.delete_batch()` / `_raw_delete()` rather than through `QuerySet.delete()`, so the
package still offers no operation that deletes an acceptance while the project's configured
behaviour still works. Removing one account touches nobody else's records because the collector is
scoped to that account's rows, and FR-015 has a test either way.

A surviving record keeps `subject`, so FR-014's two halves both hold: it still says whose it is, and
`Acceptance.objects.for_subject(...)` still finds that person's records together.

### Reading

On `Document`, because that is what the question is about:

- `Document.objects.outstanding_for(user)` — every document with a version in force that this person
  has not accepted, as a `DocumentQuerySet`. One query, whatever the number of documents (FR-012,
  FR-018, SC-005); `research.md` R4 has the shape and why each clause is there.
- `document.is_outstanding_for(user)` — FR-011, implemented as that queryset narrowed to this
  document's primary key. One rule, one implementation. `False` when nothing is in force, which is
  US-3 scenario 5 and a normal answer rather than an error.

On `Acceptance`, for the features that read a person's history:

- `Acceptance.objects.for_person(user)` — that person's records, in the order they happened.
- `Acceptance.objects.for_subject(subject)` — the same, by the stored identifier, which is the one
  that still works after the account is gone. `for_person()` is a thin call through
  `subject_of()` into `for_subject()`.

Nothing here filters by whether a site enforces a document. D4 is explicit that enforcement is R5's,
and a policy baked into the record layer is a policy that cannot change without touching evidence
handling.

### Settings

| Setting | Default | What it decides |
|---|---|---|
| `MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL` | `True` | Whether a person's acceptances outlive the removal of their account (FR-013, D1) |
| `MVP_COMPLIANCE_RECORD_IP_ADDRESS` | `False` | Whether an acceptance also holds the address the request came from (FR-016, Article XV) |

Both are read with `getattr(settings, ..., default)` at the point of use, and neither gets a
configuration object. Article III: two settings read in two places do not need a layer between the
caller and the work, and `MVP_COMPLIANCE_RENDERER` set the precedent on main.

The default of the first is the package's own position, and its cost is stated rather than hidden:
under it, closing an account does not remove what is held about that person here. That goes in the
documentation this feature ships, not only in a docstring — D1.

### Exceptions

`mvp_compliance/exceptions.py` gains two, both subclassing `Exception`, matching the shape the module
already has:

- `RecordedAcceptanceError` — an attempt to change or delete an acceptance.
- `RecordError` — recording refused: the version is a draft, or the user has no account to name.

Neither subclasses `ValidationError`, for the reason `tests/test_exceptions.py` already asserts about
the other two: a `ValidationError` is a message for a form, there is no form in this feature, and
swallowing an invariant breach into a form error is the silent discard FR-005 forbids.

## Phases

**Foundational** (sequential, before any story): `tests/factories.py` gains a `UserFactory` over the
configured user model, and `tests/conftest.py` a `user` fixture, because every story below needs a
person. No other scaffolding: the app, its migrations directory and its conformance declarations are
all on main from FS-001.

Then the stories in priority order, dispatched one at a time into the main checkout. They are not
independent — they are five layers of one model — which is why they are sequential rather than
parallel.

| Story | Priority | What it adds |
|---|---|---|
| US-1 | P1 | `Acceptance` with `user`, `subject`, `version`, `accepted_at`; `subject_of()`; `record()` and its draft refusal; `RecordError` and `RecordedAcceptanceError`; all four refusal routes and `use_in_migrations`; the first migration; factories, fixtures and the model's documentation |
| US-2 | P1 | The `one_acceptance_per_person_per_version` constraint, `get_or_create()` in `record()`, `Meta.ordering`, and the concurrency test |
| US-3 | P1 | `DocumentQuerySet.outstanding_for()`, `Document.is_outstanding_for()`, the query-count guard, and their documentation |
| US-4 | P2 | `keep_or_remove_acceptances`, the survival setting, `for_person()` / `for_subject()`, and the documentation of the default's cost |
| US-5 | P2 | `ip_address`, the evidence setting, reading `REMOTE_ADDR`, and the CHANGELOG entry naming the personal data it holds |

US-1 carries the immutability routes rather than deferring them to a story of their own, because the
spec puts them in US-1 and SC-001 asks for one test per route with none left untested. Splitting the
model from its guard would leave a window in which an acceptance is an ordinary editable row.

**Convergence** (S5, Forge): squash the stories' migrations into one `0002_*` file, run the cleanup
pass over the feature diff, and record the ADR verdict for every entry in `decisions.md`.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| The person is held twice — a foreign key and a `subject` column | FR-013 clears the foreign key under the package's default, and FR-014 requires the record to still say whose it is and to still be findable with that person's others | A foreign key alone. Under the default it becomes null and the record documents nothing, which is the failure D5 exists to prevent. An email or login name instead: a recreated account inherits the old records, which is wrong and looks right (`research.md` R5) |
| The unique constraint is over `subject` rather than `user` | It has to hold for records whose account is gone, and it must not be defeasible by the foreign key being cleared | A constraint over `user`: two records for one person become permitted the moment their account is removed, which is exactly when nobody is watching |
| A callable `on_delete` rather than a fixed rule | FR-013 asks for a setting, and `on_delete` is otherwise fixed when the class is built | A fixed `SET_NULL` plus a signal receiver that deletes when the setting says so: two mechanisms for one decision, running in an order nothing guarantees, and a signal is skipped by exactly the bulk paths an administrator tidying up accounts would use |
| `accepted_at` is set in `record()` rather than `auto_now_add=True` | An append-only record's timestamp is a value, not a write behaviour. `auto_now_add` also rewrites the field on every save, which contradicts the row being finished | `auto_now_add=True`: shorter, and it makes the one field that says *when* the thing happened a property of the write rather than of the fact |
