# Implementation Plan: Documents that are read but never agreed to

**Branch**: `007-read-only-documents` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-read-only-documents/spec.md`

## Summary

One field, one filter, three refusals, one condition on the page, one admin column.

`Document` gains `kind`, a choice between `Document.Kind.AGREED` (a document people agree to, the
default) and `Document.Kind.NOTICE`. `DocumentQuerySet.outstanding_for()` keeps only documents
people agree to. That covers every route that asks the question, because
`Document.is_outstanding_for()` already goes through that method. Recording an acceptance of a
notice's version is refused with `RecordError` by `AcceptanceManager.record()`, by
`Acceptance.save()` on a new row, and by `AcceptanceQuerySet.bulk_create()`. A notice's page leaves
out the "Agreed on" part of the line under its name. The admin's document list gains a "Kind"
column. The add and change forms already carry the field, because the admin shows every editable
field.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.13)

**Primary Dependencies**: Django 5.2, 6.0 and 6.1, django-mvp `>=0.25.0`. **No new dependency.**

**Storage**: one migration, `0008_document_kind.py`, adding `Document.kind` with the default
`"agreed"`. `AddField` with a default fills every existing row with it, so every existing document
is a document people agree to after the upgrade and no version or acceptance is touched (FR-011).
Schema only: no `RunPython`, which `tests/test_migrations.py` forbids (ADR 0004).

**Testing**: pytest + pytest-django, factories in `tests/factories.py`. `DocumentFactory` is
unchanged: a notice is `DocumentFactory(kind=Document.Kind.NOTICE)`.

**Target Platform**: a reusable Django app.

**Constraints**: `outstanding_for()` stays one query (FR-010, SC-004): the kind is a column on the
row the query already reads, so the filter adds a `WHERE` term and no join.

**Scale/Scope**: a site has tens of documents.

## Constitution Check

Read before planning and re-checked after the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Testing | Every scenario is a queryset result, a raised `RecordError` with no row created, a status code with rendered HTML, or an admin response. The failing test comes first on every task | Pass |
| II Simplicity | One `CharField` with two choices and a default. One `WHERE` term. No setting, no new model, no new view | Pass |
| III Anti-Abstraction | No base class or helper module: the refusal is one static method, `Acceptance.refuse_if_notice()`, called from the three places a row is written | Pass |
| IV Integration-First | `Document.Kind`, the `kind` field and the refusal are the contract a host project codes against. Each is tested through the public route (`record()`, `outstanding_for()`, the page, the admin) | Pass |
| V Security & data-safety | No new input surface outside the admin's existing document form, behind the existing change permission. The kind is a `choices` field, so the form refuses any other value | Pass |
| VI Documentation | `docs/models.md`, `docs/pages.md`, `docs/authoring.md`, `CONTEXT.md` (*Notice*, FR-014), README feature list, CHANGELOG, each in the story that introduces the name | Pass |
| VII Dependency discipline | Nothing added | Pass |
| VIII Internationalization | The field's `verbose_name` and `help_text`, both choice labels and the refusal message are wrapped. The `en` catalog is regenerated | Pass |
| IX Data-model conventions | `kind` is deliberately not indexed: a two-valued column on a table of tens of rows, only ever read in the same query as the document's other columns (decisions.md D2). `verbose_name` and `help_text` set. One migration | Pass |
| X Cohesion | The filter lives on `DocumentQuerySet`, the refusal on `Acceptance` and its manager and queryset, the page condition on the existing mixin | Pass |
| XI Never written to | No version or acceptance is written by this feature. Changing the kind writes only the document row. The new refusals only ever stop a row being created | Pass |
| XII Pages serve the stored HTML | Unchanged. A notice's page writes `version.html` like any other | Pass |
| XIII No claim of compliance | *Notice* and *impressum* describe what a document is. Nothing says that publishing one satisfies a law | Pass |
| XIV Personal data is declared | The kind describes a document, not a person | Pass |
| XV Compatibility | A new field with a default, a new refusal. The CHANGELOG records both. Every existing document and record is carried forward (FR-011, tested) | Pass |

## Design

### The field (US-1)

In `mvp_compliance/models.py`:

```python
class Document(models.Model):
    class Kind(models.TextChoices):
        AGREED = "agreed", _("Agreed to")
        NOTICE = "notice", _("Notice")

    kind = models.CharField(
        _("kind"),
        max_length=10,
        choices=Kind.choices,
        default=Kind.AGREED,
        help_text=_(
            "Whether people agree to this document, such as a privacy policy, or only "
            "read it, such as an impressum. Nobody is ever asked to accept a notice."
        ),
    )
```

`Document.Kind` rather than a boolean, because the spec names two kinds and the admin column and
the form should say which one in words (decisions.md D1). The kind is not frozen by publication:
neither `Document.save()` nor `DocumentQuerySet.update()` gains a guard for it (FR-007).

### What is outstanding (US-1)

`DocumentQuerySet.outstanding_for()` gains `kind=Document.Kind.AGREED` in the filter it already
applies. `Document.is_outstanding_for()` asks through it and needs no change (FR-003). The docstring
says that a notice is never outstanding.

Acceptances recorded before a document became a notice are not treated differently: the method
still excludes documents whose version in force the user accepted. So when a notice is made a
document people agree to again, an acceptance of its version in force counts at once (US-2
scenario 6, edge case 3). Nothing is written when the kind changes.

### Refusing an acceptance of a notice (US-1)

The rule: an acceptance can never be created for a version whose document is a notice. It is
checked where a row is created, and nowhere else, because an acceptance recorded before the document
became a notice must stay exactly as it is (FR-007).

- `Acceptance.refuse_if_notice(version)`, a static method, raises `RecordError` with *"Cannot record
  an acceptance of a notice. A notice is published to be read, and nobody agrees to it."* when the
  version's document is a notice. It reads the kind from the database with
  `Document.objects.filter(pk=version.document_id).values_list("kind", flat=True)` rather than from
  `version.document`, so a document instance cached before the kind changed cannot let a record
  through.
- `AcceptanceManager.record()` calls it after the existing "never published" refusal and **before**
  `get_or_create()`. The order matters: `get_or_create()` first looks for an existing row, so for a
  document made a notice after a user accepted it, a check inside `save()` alone would never run and
  `record()` would hand back the old record as if the acceptance had just been recorded (edge case
  4 requires a refusal every time).
- `Acceptance.save()` calls it when the row is being created, which covers
  `Acceptance.objects.create()`, `get_or_create()` called directly, and a hand-built instance
  (FR-004 "every route that records an acceptance", SC-002).
- `AcceptanceQuerySet.bulk_create()` refuses the whole batch when any of its versions belongs to a
  notice, with one query over the batch's document ids, before anything is written. `bulk_create()`
  never calls `save()`, so without this it would be the one route left open.

`RecordError` is the existing exception for "this acceptance cannot be recorded" (ADR 0003). No new
exception class.

### The page (US-1)

`VersionSubtitleMixin.get_page_subtitle()` returns the version line alone when the version's
document is a notice, before it looks for an acceptance. A notice's page therefore never says the
reader agreed to it, whether or not an acceptance from before the change exists (FR-006, edge case
2). `DocumentView.get_version()` reads versions through `self.object.versions`, whose results
already carry `self.object` as their `document`, so the check costs no query.

Nothing else on the page changes. `Document.objects.in_force()` does not filter by kind, so the
list beside the wording carries both kinds (scenario 8) and a notice with only drafts is "not found"
like any other document (edge case 1).

### The admin (US-2)

`DocumentAdmin.list_display` gains `"kind"` after `"name"` (FR-009, scenario 1). `DocumentAdmin`
declares no `fields` or `fieldsets`, so the add and change forms already carry every editable field,
`kind` included, with the default preselected (scenarios 2 and 3). The slug freeze in
`get_readonly_fields()` does not touch it.

### The announcement

Unchanged. `version_published` is sent for any publication (edge case 5). US-1 carries one test
that publishing a notice's version sends it.

### Demo

`seed_demo` gains an "Impressum" notice with one published version (slug `impressum`, added to
`SLUGS`). `make_document()` gains a `kind` argument defaulting to a document people agree to. The
landing page links the impressum beside the other two documents. This is what the walkthrough
shows: a signed-in user sees its page with no agreement line, and the admin list shows its kind.

### Documentation

- US-1: `docs/models.md` (the `kind` field and `Document.Kind` under `Document`; the *Outstanding*
  section says a notice is never outstanding; the `Acceptance` section says recording against a
  notice is refused, and by which routes), `docs/pages.md` (a notice's page carries no agreement
  line; linking an impressum from the footer), `CONTEXT.md` **Notice** (FR-014), README feature
  list, CHANGELOG Added entry, `en` catalog.
- US-2: `docs/authoring.md` (a new section, *Documents people agree to, and notices*: choosing the
  kind, changing it later, what happens to recorded acceptances; *The documents list* names the new
  column), `docs/models.md` (changing the kind from code).

## Stories and order

| Story | Issue | Builds on | Order |
|---|---|---|---|
| US-1 Publishing a notice nobody is asked to accept | #74 | main | 1 |
| US-2 Seeing and changing which kind a document is | #75 | US-1's `kind` field | 2 |

Sequential, in one worktree: US-2's admin and kind-change tests need the field US-1 adds.

## Complexity Tracking

None. No new dependency, abstraction or infrastructure.

## Outside this plan

- Per-document enforcement and the site-wide check (the rest of R5).
- The account area's list of what a person agreed to (#66). It can read `Document.Kind` when it is
  built.
