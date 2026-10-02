# Implementation Plan: What a person has agreed to, in their account area

**Branch**: `008-agreed-documents-in-account-area` | **Date**: 2026-10-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/008-agreed-documents-in-account-area/spec.md`, and the
prototype approved on screen, recorded in [sketch.md](./sketch.md).

## Summary

One page, one menu entry, one reserved slug, and a new layout for the document page.

`AgreedDocumentsView` serves the signed-in person's own list at `agreed/` under the package's pages.
It reads their acceptances of documents people agree to in one query and the versions in force in a
second, groups them by document, and marks a document whose version in force they have not accepted.
A document with more than four accepted versions shows three and folds the rest. The page extends
django-mvp's account layout, and an entry appended to `AccountCenterMenu` puts it in the area's
menu. Without the account area the page answers "not found". The slug `agreed` is refused by a
validator on `Document.slug`. The document page puts its list of documents in a card in a column of
its own, pinned below the top bar while the document scrolls.

The templates, markup and wording were approved on the prototype and are kept as they are. The
Python behind them is removed first and rebuilt test-first.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.13)

**Primary Dependencies**: Django 5.2, 6.0 and 6.1, django-mvp `>=0.25.0`. `django-flex-menus` becomes
a direct dependency: it is already installed through django-mvp, and the menu entry imports
`MenuItem` from it (see Complexity Tracking).

**Storage**: one schema-only migration, `0009`, recording the new validator on `Document.slug`. No
column changes and no row is touched. No `RunPython`, which `tests/test_migrations.py` forbids
(ADR 0004).

**Testing**: pytest + pytest-django, factories in `tests/factories.py`, unchanged. Requests through
`client`. The projects that leave part out are tested with `@override_settings(ROOT_URLCONF=...)`
against two small URLconf modules under `tests/`.

**Target Platform**: a reusable Django app.

**Constraints**: two queries for the list whatever its length (FR-015, SC-005). The page writes
nothing (FR-016).

**Scale/Scope**: tens of documents on a site, and up to dozens of accepted versions for one person.

## Constitution Check

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Testing | Every scenario is a list of records in the response context and the rendered page, a link target, a redirect, a status code, a query count, or a validation error code. Layout and wording are not tested. The failing test comes first on every task that changes behaviour | Pass |
| II Simplicity | One view, one queryset method, one validator. No setting, no model, no template tag | Pass |
| III Anti-Abstraction | No base class or mixin for "a page in the account area": there is one such page | Pass |
| IV Integration-First | Tests go through the mounted addresses and the processed menu, in a project with the area, without it, and without the package's pages | Pass |
| V Security & data-safety | The page takes no parameter and reads `request.user` only. Sign-in is required. Document names go through the template's escaping. Read-only: no form, and no method but `GET` and `HEAD` | Pass |
| VI Documentation | `docs/pages.md`, `docs/models.md`, README feature list and CHANGELOG, each in the story that introduces the name | Pass |
| VII Dependency discipline | `django-flex-menus` named directly because it is imported directly. Nothing new is installed | Pass, justified below |
| VIII Internationalization | Every new string is wrapped, and the `en` catalog is regenerated | Pass |
| IX Data-model conventions | No new field. One migration for the validator | Pass |
| X Cohesion | The query lives on `AcceptanceQuerySet`. Grouping lives on the view, as a method. The validator sits beside the existing slug validator | Pass |
| XI Never written to | The page reads. A test asserts no acceptance, disclosure, version or document row changes when it is opened | Pass |
| XII Pages serve the stored HTML | The list links to version pages and renders no wording of its own | Pass |
| XIII No claim of compliance | Strings say *agreed*, *in force*, *replaced*. The existing sweep over page templates covers the new ones | Pass |
| XIV Personal data is declared | Nothing new is stored. A person's own records are shown to that person only | Pass |
| XV Compatibility | The slug `agreed` becomes unavailable and the document page's markup changes. Both go in the CHANGELOG | Pass |

## Design

### What is kept from the prototype, and what is rebuilt

Kept as approved: `agreed_documents.html`, `_agreed_version_rows.html`, `document_detail.html`,
`static/mvp_compliance/pages.css`, and the demo's seed data and landing page.

Rebuilt: `AgreedDocumentsView`, the route and `menus.py`. A foundational task removes them, so each
comes back behind a failing test. The same task teaches the two helpers behind the string tests to
read a plural, because the list's template holds the package's first one. No assertion changes. The demo's link to the list is removed with them and returns with
the route.

### The query (US-1)

`AcceptanceQuerySet.of_agreed_documents()`, with its manager forwarder (ADR 0006):

```python
def of_agreed_documents(self) -> "AcceptanceQuerySet":
    """Narrow to acceptances of documents people agree to, each with its version and document.

    Ordered by the document's name, then by publication, newest first.
    """
    return (
        self.filter(version__document__kind=Document.Kind.AGREED)
        .select_related("version__document")
        .order_by("version__document__name", "-version__published_at")
    )
```

The page calls `Acceptance.objects.for_person(request.user).of_agreed_documents()`. Matching goes
through `for_person()`, so the list follows the identifier the records were written under (spec
assumption 4). A notice is left out by its kind today, so one that is made a document people agree
to again comes back with its acceptances untouched (edge case 2).

### The view (US-1, US-2, US-3)

`AgreedDocumentsView(LoginRequiredMixin, MVPTemplateView)` in `mvp_compliance/views.py`:

- `http_method_names = ["get", "head"]`. There is nothing to submit (FR-010).
- `dispatch()` answers `Http404` when `account-center` does not reverse, before it calls
  `super().dispatch()` and so before the sign-in redirect, so a
  project without the account area has no such page for anyone (FR-013).
- The route takes no argument and the view reads only `request.user` (FR-004).
- `get_entries()` returns one entry per document: the document, `shown`, `earlier` and `newer`.
  - US-1 builds the grouping and the split. `shown_first = 3`: with more than `shown_first + 1`
    accepted versions the first three are `shown` and the others `earlier`; otherwise all are
    `shown` (FR-019). The attribute is the one place the number lives.
  - US-2 adds `newer`: the version in force when none of the person's acceptances is of it, read
    with `Version.objects.current().filter(document__in=...)`, and `None` otherwise (FR-009). It is
    computed on each request, so a publication shows up with nothing done by anyone (US-2
    scenario 5).
- `get_breadcrumbs()` returns the account area's crumb, linked, then this page.
- The title and subtitle are the approved wording, as lazy translations.

### The route and the reserved slug (US-1, US-3)

`mvp_compliance/urls.py` lists `path("agreed/", ..., name="agreed")` ahead of the slug route.

`Document.RESERVED_SLUGS = frozenset({"agreed"})` and a validator `unreserved_slug` beside
`lowercase_slug`, raising `ValidationError(code="reserved")`. It joins `Document.slug`'s
`validators`, so the admin form refuses the slug where it already refuses capitals (US-3
scenario 4).

The validator runs where field validators run: forms and `full_clean()`. Code that calls
`Document.objects.create(slug="agreed")` is not stopped, which matches how `lowercase_slug` already
behaves, and the route order still keeps the list's address from answering with that document.

### The menu entry (US-1, US-3)

`mvp_compliance/menus.py`, found by the menu library's autodiscovery:

```python
AccountCenterMenu.append(
    MenuItem(
        name="agreed-documents",
        view_name="mvp_compliance:agreed",
        extra_context={"label": _("Agreements"), "icon": "document"},
    )
)
```

No `check`: the area's landing page already requires sign-in, and the entry is dropped when the
package's pages are not mounted because its address does not reverse.

`TestNoMenuEntry.test_the_package_does_not_touch_the_menu_library` is narrowed to what FS-006's
FR-014 asks: no module in the package names `AppMenu` or `MobileFooterMenu`, the project's own menus
(decisions.md D2).

### The pages (kept as approved)

The list: one card per document in a single column. Each card carries the statement about a newer
version when there is one, a two-column table of the versions shown, and a `<details>` holding the
earlier ones under a line that counts them. The empty state uses `c-page.list.empty`.

The document page: `page.content-wrapper` is overridden so the list of documents is a card in the
left column, titled "Documents", and the title, version menu, alert and wording are the right
column. The card is sticky on wide screens. Its offset is `--mvp-compliance-header-clearance`
(5rem) in `pages.css`, because the shell's stylesheet has no utility for it. Nothing about what the
page shows or who can read it changes, and its existing tests pass unchanged.

### Demo

The seed command publishes and accepts on past dates and seeds the accounts that reach each state
(sketch.md). It stays as it is.

### Documentation

- Foundational: `docs/pages.md` describes the document page's two columns and the custom property.
  CHANGELOG *Changed*: the document page's markup.
- US-1: `docs/pages.md` gains a section on the list: what it shows, the folded history, that it is
  the reader's own records. `docs/models.md`: `of_agreed_documents()`. README feature list.
  CHANGELOG *Added*. The `en` catalog is regenerated in each task that adds a string.
- US-3: `docs/pages.md`: what a project mounts for the page to appear, and that it is left out
  safely (FR-018). `docs/models.md`: the reserved slug. CHANGELOG: the slug `agreed` is no longer
  available, and what happens to a document already published under it.

## Stories and order

| Story | Issue | Builds on | Order |
|---|---|---|---|
| Foundational | n/a | the prototype on this branch | 0 |
| US-1 Seeing what I agreed to, where I manage my account | #78 | Foundational | 1 |
| US-2 Knowing a newer version is in force | #79 | US-1's view | 2 |
| US-3 A project that leaves part of it out | #80 | US-1's view, route and menu entry | 3 |

Sequential, in one worktree. US-2 and US-3 both edit the view US-1 builds.

## Complexity Tracking

| Addition | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| `django-flex-menus` as a direct dependency | `menus.py` imports `MenuItem` from it, and `deptry` refuses an import that is only installed transitively | Importing `MenuItem` through `mvp.menus` relies on a name django-mvp does not export on purpose |

## Outside this plan

- Asking a person to accept the version in force (R4).
- Cookie choices on this page (the other half of R9).
- The rest of issue #71: the version menu, the version line and how an earlier version is marked.
