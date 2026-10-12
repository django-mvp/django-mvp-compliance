# Implementation Plan: Asking a signed-in person to agree to what is outstanding

**Branch**: `009-asking-to-agree` | **Date**: 2026-10-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/009-asking-to-agree/spec.md`, and the prototype
approved on screen, recorded in [sketch.md](./sketch.md).

## Summary

One page, one manager method, one setting, one reserved slug and a few lines of script.

`AgreementView` serves the page at `agree/` under the package's pages. It lists every document
outstanding for the signed-in person, each with a link to the page of its version in force and a
toggle. A submission records the agreed versions in one write through
`Acceptance.objects.record_many()`, asks again what is outstanding, and sends the person on to
`next` only when the stored records leave nothing required. A failed write is logged and brings
the page back with the toggles kept. A person with nothing outstanding is redirected without the
page being drawn.

The templates, markup and wording were approved on the prototype and are kept as they are. The
Python behind them is removed first and rebuilt test-first.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.13)

**Primary Dependencies**: Django 5.2, 6.0 and 6.1, django-mvp `>=0.25.0`. Nothing new.

**Storage**: no migration. No field is added and `Document.slug`'s validator is unchanged.

**Testing**: pytest + pytest-django, factories in `tests/factories.py`, unchanged. Requests through
`client`. Cross-site submissions through `Client(enforce_csrf_checks=True)`.

**Target Platform**: a reusable Django app.

**Constraints**: the same number of queries to show the page and to process a submission whatever
the number of documents (FR-023, SC-009). Opening the page writes nothing (FR-006).

**Scale/Scope**: a handful of documents outstanding for one person at a time.

## Constitution Check

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Testing | Every scenario is a record written or not written, a redirect target, a status code, a context value, a hook a script depends on, a log record or a query count. Wording, layout and badge variants are not tested | Pass |
| II Simplicity | One view, one manager method, one setting. No form class, no model, no signal, no template tag | Pass |
| III Anti-Abstraction | No base class. Two small methods on the view are overridden by the demo today and are where the site-wide check plugs in (decisions.md D16) | Pass, justified below |
| IV Integration-First | Tests go through the mounted address with a signed-in client, in a project with the package's pages and in one without | Pass |
| V Security & data-safety | Sign-in required. CSRF protection is Django's and is tested. The destination is checked with Django's own host check. A submitted version id is only honoured when it is the current version of a document outstanding for that person. Document names go through template escaping. The cause of a failure is never rendered | Pass |
| VI Documentation | `docs/pages.md`, `docs/models.md`, README and CHANGELOG, each in the story that introduces the name | Pass |
| VII Dependency discipline | Nothing new | Pass |
| VIII Internationalization | Every string is wrapped, fixed, and free of interpolated names. The `en` catalog is regenerated | Pass |
| IX Data-model conventions | No new field | Pass |
| X Cohesion | The batch write lives on `AcceptanceManager` beside `record()`. Everything else is a method of the view | Pass |
| XI Never written to | The page only ever creates acceptances. An existing one is passed over by the unique constraint, never rewritten | Pass |
| XII Pages serve the stored HTML | The page renders no wording. It links to the version's own page | Pass |
| XIII No claim of compliance | Strings say *agree*, *required*, *optional*. The existing sweep over page templates is widened to the new template and the row component | Pass |
| XIV Personal data is declared | Nothing new is stored. The optional connecting address follows the FS-003 setting | Pass |
| XV Compatibility | The slug `agree` becomes unavailable. CHANGELOG says so | Pass |

## Design

### What is kept from the prototype, and what is rebuilt

Kept as approved: `templates/mvp_compliance/agreement.html`,
`templates/cotton/compliance/outstanding.html`, `static/mvp_compliance/agreement.js`, the demo's
seed data and its landing page card.

Rebuilt: `AgreementView`, the `agree/` route, the reserved slug. A foundational task removes them,
so each comes back behind a failing test. The demo's signal receiver and its sketch-only setting are
removed in the same task and replaced, in the stories that need them, by a view in the demo project.

The view supplies exactly the context the approved templates read: `entries` (each with
`document`, `version`, `optional` and `field`), `required_count`, `destination`,
`redirect_field_name`, and after a submission `failed`, `missing` and `changed`.

### The batch write (US-1)

`AcceptanceManager.record_many(user, versions, request=None) -> None` in `mvp_compliance/models.py`,
beside `record()`:

- raises `RecordError` if any version has never been published, before touching the database;
- builds one `Acceptance` per version with the same subject, time and optional address `record()`
  would write;
- writes them with the queryset's `bulk_create(..., ignore_conflicts=True)`, which refuses a
  notice's version in one query and passes over an acceptance that already exists.

Two queries whatever the number of versions. `record()` is left as it is.

The view's method `record_agreed(versions)` is the one place that calls it.

### The view (US-1 to US-5)

`AgreementView(LoginRequiredMixin, MVPTemplateView)` in `mvp_compliance/views.py`.

- `redirect_field_name = "next"`.
- `get_entries()`: `Document.objects.outstanding_for(request.user).in_force().order_by("name")`,
  one entry per document, required entries first. Read once per request and read again after a
  write.
- `is_optional(document) -> bool`: returns `False`. Every outstanding document is required until
  the site-wide check (#87) decides otherwise.
- `get()`: with no entries, redirect to the destination (US-4). Otherwise render.
- `post()`:
  1. `agreed` = the entries whose version id is among the submitted `agree` values. An id that is
     not the current version of a document outstanding for this person matches nothing (FR-005).
  2. `changed` = some listed entry's version id is missing from the submitted `listed` values,
     which means a version was replaced, or a document published, since the page was drawn.
  3. With something agreed: `record_agreed()` inside `transaction.atomic()`. On `DatabaseError` or
     `RecordError`: `logger.exception(...)` and render with `failed`, the submitted toggles kept
     (US-2).
  4. Read the entries again. If none is required, redirect to the destination. The decision is
     taken from this second read alone (FR-008).
  5. Otherwise render, with `missing` unless `changed`.
- `record_agreed(versions)`: `Acceptance.objects.record_many(request.user, versions,
  request=request)`.
- `get_destination()`: the `next` value from the form, else from the query string. Kept only when
  `url_has_allowed_host_and_scheme` passes for the request's host and its path is not this page's
  own. Otherwise `resolve_url(settings.MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL)`, default `/`
  (US-4).
- `get_context_data()`: builds each entry's `field` attributes: `name="agree"`, the version id,
  an id from the slug, `aria-describedby` pointing at the row's name, `data-required` on a required
  entry, `checked` when the toggle was on in a submission that failed.
- Title, subtitle and breadcrumb as approved, as lazy translations.

A person leaving the page is not this view's concern: it never stops a request for another address
(FR-024).

### The route and the reserved slug (US-1, US-5)

`mvp_compliance/urls.py` lists `path("agree/", ..., name="agree")` ahead of the slug route.
`Document.RESERVED_SLUGS` gains `"agree"`. No migration: the validator is unchanged.

### The hooks the script depends on (US-1)

`agreement.js` finds the form by the id `agreement`, the required toggles by `data-required`, and
the button by `type="submit"`. Tests assert those three hooks and that the page loads the script.
The script's behaviour has no automated test: the repository has no JavaScript runner
(research.md).

### The demo (US-2, US-3)

`demo/views.py` gains `DemoAgreementView(AgreementView)`:

- `is_optional()` answers from a list of slugs in the demo's settings, so the page can be looked at
  with required and optional documents together;
- `record_agreed()` raises `DatabaseError` for `unrecorded.user@example.com`, so the failed write
  can be looked at.

`demo/urls.py` routes `legal/agree/` to it ahead of the package's include. Both are demo-only.

### Documentation

- US-1: `docs/models.md`: `record_many()`. `docs/pages.md` gains a section on the page: what it
  lists, what a submission records.
  README feature list. CHANGELOG *Added*.
- US-2: `docs/pages.md`: what happens when an acceptance cannot be stored, and the logger to
  attach error reporting to.
- US-4: `docs/pages.md`: sending a person to the page, the `next` parameter, a person with nothing
  outstanding, `MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL`. README settings.
- US-5: `docs/pages.md`: replacing the template, and the methods a project's own view can
  override. `docs/models.md` and CHANGELOG: the slug `agree` is no longer available. `CONTEXT.md`:
  an entry for *Outstanding*.

The `en` catalog is regenerated in each task that adds a string.

## Stories and order

| Story | Issue | Builds on | Order |
|---|---|---|---|
| Foundational | n/a | the prototype on this branch | 0 |
| US-1 Agreeing to an outstanding document and carrying on | #90 | Foundational | 1 |
| US-2 Being asked again when the record could not be written | #91 | US-1's view | 2 |
| US-3 Dealing with several outstanding documents in one sitting | #92 | US-1's view | 3 |
| US-4 Sending a person to the page from a project's own code | #93 | US-1's view | 4 |
| US-5 A page that belongs to the site, with nothing to write | #94 | US-1's view and route | 5 |

Sequential, in one worktree. Every story edits the view US-1 builds.

## Complexity Tracking

| Addition | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| `record_many()` beside `record()` | FR-023: a submission's cost must not grow with the documents agreed to | A loop over `record()` costs three queries a document |
| `is_optional()` and `record_agreed()` as methods of the view | The approved page marks rows required or optional and has a failed-write state. The demo has to reach both, and the site-wide check (#87) needs the first | A setting read by the package would ship a fake of #87's decision. Inlining both would leave the approved optional rows unreachable and untested |

## Outside this plan

- Deciding when a person is sent to the page, and which documents are required (R5, #87).
- A summary of what changed between versions (R6).
- A link to this page from the document pages or the account area's list.
