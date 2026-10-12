# Implementation Plan: Applying the agreement check across the whole site

**Branch**: `010-site-wide-agreement-check` | **Date**: 2026-10-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-site-wide-agreement-check/spec.md`. Evidence for
the choices below is in [research.md](./research.md).

## Summary

One field, one queryset method, one permission, one middleware, three settings, two system checks,
and a change to when the page that asks lets a person go.

`Document.enforced` says whether a document stops anybody, and is `True` unless somebody chooses
otherwise. `Document.objects.enforced_outstanding_for(user)` is the one answer to "what stops this
user". `AgreementMiddleware` asks it for each signed-in request, redirects a user it stops to the
page that asks, and remembers in the session, for a delay the project sets, that a user was found
clear. `AgreementView.is_optional()` answers from the field, so the page and the check agree.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13)

**Primary Dependencies**: Django 5.2, 6.0 and 6.1, django-mvp `>=0.25.0`. Nothing new.

**Storage**: one migration, `0002`, adding `Document.enforced` and declaring one permission.

**Testing**: pytest + pytest-django, factories in `tests/factories.py`. The middleware is tested
through `client` with `MIDDLEWARE` extended by `modify_settings`, in a new `tests/test_middleware.py`
that mirrors `mvp_compliance/middleware.py`. System checks in a new `tests/test_checks.py`. Time is
moved by patching `django.utils.timezone.now`.

**Target Platform**: a reusable Django app.

**Constraints**: no database query added to a request from a user already found clear, until the
delay has passed (FR-021, SC-004). One query to decide whether a user is stopped, whatever the
number of documents (FR-015).

**Scale/Scope**: every signed-in request of a host project passes through the middleware.

## Constitution Check

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Testing | Every scenario is a redirect or its absence, a redirect target, a response header, a status code, a record count, a query count, a field value or a system check id. No wording is asserted | Pass |
| II Simplicity | One middleware class with no hooks for subclasses, one queryset method, three settings read with `getattr` where they are used | Pass |
| III Anti-Abstraction | No base class, no registry, no decorator for views (decisions.md D5). `is_optional()` stays the one method it already was | Pass |
| IV Integration-First | Tests send requests through the middleware stack to real views, in a project that mounts the package's pages and in one that does not | Pass |
| V Security & data-safety | The check adds a restriction and removes none. The return address is checked by the page it is passed to. A user who is being stopped is never remembered. Being let past writes nothing | Pass |
| VI Documentation | A new `docs/enforcement.md`, with `docs/models.md`, `docs/pages.md`, README, CHANGELOG and `CONTEXT.md`, each in the story that introduces the name | Pass |
| VII Dependency discipline | Nothing new. The `HX-Redirect` header is set by hand | Pass |
| VIII Internationalization | The field's `verbose_name` and `help_text`, the permission's name and the checks' messages are wrapped. The `en` catalog is regenerated | Pass |
| IX Data-model conventions | `enforced` carries `verbose_name` and `help_text`. One migration for the pull request. No index: the table holds a handful of rows | Pass |
| X Cohesion | The rule for who is stopped is on `DocumentQuerySet`. The middleware holds only what belongs to a request | Pass |
| XI Never written to | No version and no acceptance is written or changed. The migration touches `Document` only | Pass |
| XII Pages serve the stored HTML | No page content changes | Pass |
| XIII No claim of compliance | New strings say *enforced*, *agree*, *required*. None says the site or the person is compliant | Pass |
| XIV Personal data is declared | Nothing personal is stored. The session key holds a time | Pass |
| XV Compatibility | Without the middleware nothing changes (FR-002, SC-010). The new column defaults to `True`. CHANGELOG lists both | Pass |

## Design

### Enforcement on the document (US-2)

`mvp_compliance/models.py`:

- `Document.enforced = models.BooleanField(default=True)` with `verbose_name` and `help_text`. Like
  `kind`, it is not frozen by publication and is changed with an ordinary `save()` or `update()`.
- `DocumentQuerySet.enforced_outstanding_for(user)` returns
  `self.outstanding_for(user).filter(enforced=True)`, with the same forwarding method on
  `DocumentManager` that `outstanding_for` has. One query, whatever the number of documents.
- `outstanding_for()` is unchanged, so what a user has outstanding still counts an unenforced
  document (FR-012).

`mvp_compliance/admin.py`: `enforced` joins `DocumentAdmin.list_display`. The form already takes
every editable field, so the add and change forms gain it with no further change.

Migration `0002`: `AddField` with `default=True`. A test migrates to `0001`, creates a document,
a published version and an acceptance, migrates forward, and asserts the document is enforced and
the versions and acceptances are the same rows (FR-024).

### The check (US-1)

`mvp_compliance/middleware.py`, one class:

```
class AgreementMiddleware:
    def __init__(self, get_response)
    def __call__(self, request)
```

`__call__` lets the request through, by returning `self.get_response(request)`, at the first of
these that holds, in this order:

1. `request` has no `user`, or the user is not authenticated (FR-005).
2. The session holds a time under the key `mvp_compliance_clear_until` that has not passed
   (FR-021).
3. The user's `get_username()` is in `MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS` (US-5).
4. `Document.objects.enforced_outstanding_for(user).exists()` is false. Before letting the request
   through, the middleware stores the time the finding expires in the session (FR-023).
5. The user holds `mvp_compliance.skip_agreement` (US-5).
6. The page that asks does not reverse (US-1 scenario 12).
7. The requested address is one that stays reachable (below).

Otherwise it answers itself:

- for an htmx request (`HX-Request: true`), a 200 with an empty body and the header `HX-Redirect`
  set to the page's address with no return address (FR-007);
- for `GET` and `HEAD`, a redirect to the page's address with `next` set to
  `request.get_full_path()`, percent-encoded (FR-004);
- for any other method, a redirect to the page's address with no `next`.

The view of the address that was asked for is never called (US-1 scenario 7).

Steps 3 and 5 belong to US-5, and the setting for the delay in step 4 to US-6. US-1 builds the
class with steps 1, 2, 4, 6 and 7 and a delay of sixty seconds held in a module constant.

Only step 4 writes to the session, so a user who is being stopped, a user let past by name and a
user let past by the permission are each asked about afresh on every request.

### What stays reachable (US-1, US-4)

A method of the middleware, `is_reachable(request) -> bool`, true when any of these holds:

- the path is the path of `reverse("mvp_compliance:agree")`;
- `resolve(request.path_info)` succeeds and its `app_names` include `mvp_compliance`, or its
  `view_name` is `account_logout`, `logout` or `admin:logout`;
- the path is beneath `STATIC_URL` or `MEDIA_URL`, when that setting is a path on this site;
- the path is beneath an entry of `MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS` (US-4).

"Beneath" is compared a path segment at a time: an entry `/help/` covers `/help`, `/help/` and
`/help/faq/`, and does not cover `/helpful/`. The project's entries are added to the defaults and
never replace them (FR-017).

A path that resolves to nothing is not reachable, so the user is redirected.

### Letting accounts past (US-5)

- `MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS`: a list of the values accounts sign in with, empty by
  default, compared with `user.get_username()`.
- `Document.Meta.permissions` gains `("skip_agreement", _("Can continue without accepting enforced
  documents"))`, checked with `user.has_perm("mvp_compliance.skip_agreement")`. It joins migration
  `0002`, which is regenerated so the branch still adds one migration.

Neither writes anything (FR-020). The permission is asked only of a user the outstanding query has
just said would be stopped, so it costs nothing for anybody else (US-5 scenario 6).

### The delay (US-6)

`MVP_COMPLIANCE_AGREEMENT_CHECK_INTERVAL`: seconds, default `60`. With `0` nothing is stored and
nothing stored is honoured, so every request is checked against the database (FR-022).

### The system checks (US-1)

`mvp_compliance/checks.py`, registered from `MvpComplianceConfig.ready()`. Both run only when
`mvp_compliance.middleware.AgreementMiddleware` is in `MIDDLEWARE`:

- `mvp_compliance.E001`: `reverse("mvp_compliance:agree")` fails. The hint gives the `include()`
  line.
- `mvp_compliance.E002`: no entry before the check is `AuthenticationMiddleware` or a subclass of
  it. The hint says where to move it.

### The page that asks (US-3)

`mvp_compliance/views.py`, two changes to `AgreementView`:

- `is_optional(document)` returns `not document.enforced`. Its docstring stops saying every
  document is required.
- `get()` redirects to the destination when no entry is required and either there are no entries
  or the request carries the `next` parameter, whatever its value (FR-030, and the edge case of a
  return address that cannot be followed). With no `next` and optional entries it draws the page
  (FR-031).

`post()` is unchanged. It already sends a person on when every remaining entry is optional, records
whatever was agreed to, and keeps a person whose required write failed (FR-028, FR-029, US-3
scenario 10). With no `next` the destination is the default one (FR-031).

The demo's stand-in goes with it: `DemoAgreementView.is_optional()` and
`DEMO_OPTIONAL_DOCUMENT_SLUGS` are removed, and the seed command marks the same document as not
enforced. `DemoAgreementView.record_agreed()` stays.

### FS-009's specification (foundational)

`specs/009-asking-to-agree/spec.md` is edited so FR-008, FR-012 and FR-018, the scenarios that
rest on them, and the Scope and Assumptions lines that say the page treats every document alike
read as current (FR-033). Prose only.

### The demo

- `demo/settings.py`: the middleware after `AuthenticationMiddleware`, one named account, and the
  landing page's address listed as reachable so the list of demo accounts can be read by a user who
  is being stopped.
- `seed_demo`: `house-rules` not enforced; an account in a group that holds the permission.
- The landing page's account list names the two accounts that are let past.

### Documentation

- `docs/enforcement.md` (new): switching the check on and where the middleware goes; what stays
  reachable and how to add to it; a request for part of a page; letting accounts past, that a
  superuser always is, and what each way costs; the delay; the two system checks.
- `docs/models.md`: `enforced`, `enforced_outstanding_for()`, the permission.
- `docs/pages.md`: when the page lets a person go, how a person accepts a document that is not
  enforced, and `is_optional()` reading the field.
- README: feature list, installation step, settings table, documentation index.
- `CONTEXT.md`: *Enforcement* says it is set on the document, that a new document is enforced, and
  that it only takes effect on a site that has switched the check on (FR-027).
- `CHANGELOG.md`: *Added* and *Changed*.

## Requirement coverage

| Requirement | Tasks |
|---|---|
| FR-001, FR-002, FR-003, FR-005, FR-008, SC-001, SC-002, SC-010 | T006, T007 |
| FR-004, FR-007 | T006, T007 |
| FR-006, SC-003 | T006, T007 |
| FR-009 | T008, T009 |
| FR-010, FR-011, FR-012, FR-013, SC-006 | T002, T003 |
| FR-014 | T004, T005 |
| FR-015 | T002, T003, T011 |
| FR-016, FR-017 | T014, T015 |
| FR-018, FR-019, FR-020, SC-007 | T016, T017 |
| FR-021, SC-004 | T006, T007, T016 |
| FR-022, SC-005 | T018, T019 |
| FR-023 | T006, T007 |
| FR-024 | T002, T003 |
| FR-025 | T003, T009, T017 |
| FR-026 | T010, T013, T015, T017, T019 |
| FR-027 | T005 |
| FR-028, FR-029, FR-030, FR-031, FR-032, SC-008, SC-009 | T011, T012 |
| FR-033 | T001 |

## Complexity Tracking

Nothing in the Constitution Check needs justifying.
