# Implementation Plan: Documents and their versions readable as pages of the site

**Branch**: `006-documents-readable-as-pages` | **Date**: 2026-09-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-documents-readable-as-pages/spec.md`

## Summary

One field, one guard, four read-only views, four templates, one URL module.

`Document` gains `slug`. Once the document has a published version, `Document.save()` and the
queryset's `update()` refuse a change to it, the same way they refuse a change to a published
version's wording. The admin suggests it from the name and shows it read-only once it is fixed.

`mvp_compliance/urls.py` (`app_name = "mvp_compliance"`) gives a host project four addresses to mount
under a prefix of its choosing: the document index, a document's page, its version list, and a
version's page. Each is an MVP view, so it renders inside the django-mvp shell through the packaged
`page_view.html`, and each template fills `page.content` only. A version's wording is its stored
`html`, written out unaltered (Article XIII).

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.13)

**Primary Dependencies**: Django 5.2, 6.0 and 6.1, django-mvp (0.24.0 resolved, floor `>=0.23.0`
unchanged). **No new runtime dependency.** `MVPDetailView` and `MVPTemplateView` from `mvp.views`,
a registered path converter, a `Subquery` annotation.

**Storage**: one migration, `0007_document_slug.py`: `Document.slug`, a unique `SlugField`. Nothing
has been released and no site uses the package, so no existing document is carried forward (spec
Clarifications). A development database holding more than one document is rebuilt with
`seed_demo` rather than migrated.

**Testing**: pytest with pytest-django, `tests/settings.py`, SQLite. Views are tested through the
test client against `tests/urls.py`, which mounts the package under `legal/`. Query counts through
`django_assert_num_queries`, comparing a small and a larger data set. Factories per Article X:
`DocumentFactory` gains a slug sequence.

**Target Platform**: a Django project that has installed django-mvp.

**Project Type**: installable Django application. Every page added here is something a person
reads, so the diff is walked through on the demo project before the merge gate.

**Constraints**: Article XII (a published document's slug joins what is never written to),
Article XIII (pages serve the stored HTML, never a render), Article XIV (no page, template or doc
line claims compliance or names a regulation), Article VIII (every template string translatable),
Article XVI (template names become public surface, recorded in the CHANGELOG).

**Scale/Scope**: one field, one migration, four views, four templates, one URL module, one
annotation, admin changes, demo and test settings, four stories, 22 functional requirements.

## Constitution Check

Read before planning and re-checked after the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every scenario is a status code, a query count, or an assertion on rendered HTML. The failing test comes first on every task | Pass |
| II Simplicity | Django's `DetailView` machinery through mvp, `get_object_or_404`, one annotation. No caching, no sitemap, no settings | Pass |
| III Anti-Abstraction | Four small view classes that share one queryset method each. No base class of the package's own beyond what mvp provides | Pass |
| IV Integration-First | The URL names and template paths are the contract a host project codes against. Both are fixed in the story that introduces them and documented there | Pass |
| V Security & data-safety | The document name is autoescaped everywhere. The version's `html` is written with `safe` because it was sanitised against an allow list at publication (`rendering.py`) and is never user input at request time. Drafts are unreachable by construction: every queryset starts from `published()` or `current()` | Pass |
| VI Documentation | `docs/pages.md` is new and linked from the README. `docs/models.md` and `docs/authoring.md` gain the slug. CHANGELOG Added entries | Pass |
| VII Dependency discipline | No new runtime dependency | Pass |
| VIII Internationalization | Every template string in `{% trans %}`/`{% blocktrans %}`, every Python string in `_()`. The `en` catalog regenerated | Pass |
| IX Data-model conventions | `slug` is `unique=True`, which is its index and the lookup every page makes. `verbose_name` and `help_text` set | Pass |
| X Test structure | `tests/test_views.py` mirrors `views.py`, `tests/test_urls.py` mirrors the converter in `urls.py`. Model and admin behaviour stay in their existing files | Pass |
| XI Cohesion | The converter is a class in `urls.py`, where Django looks for it. Queryset behaviour lives on the querysets | Pass |
| XII Immutable publication | The slug joins the published content that `save()` and `update()` refuse to change | Pass |
| XIII Pages serve the stored HTML | Templates write `version.html`, nothing renders Markdown. A test compares the response bytes with the stored field | Pass |
| XIV Mechanics, not compliance | Pages say "in force", "replaced", "version". Nothing says compliant or names a regulation | Pass |
| XV Personal data | The slug identifies a document, never a person. The pages show no publisher | Pass |
| XVI Compatibility | New field, new templates, new URL names. CHANGELOG records them. No data carried forward because none exists in the wild | Pass |

## Design

### The slug (US-1 introduces it, US-4 fixes it)

On `Document`, after `name`:

```python
slug = models.SlugField(
    _("slug"),
    max_length=100,
    unique=True,
    validators=[lowercase_slug],   # module-level RegexValidator: ^[a-z0-9]+(?:-[a-z0-9]+)*$
    help_text=...,                 # the document's identifier in its address; fixed once a
                                   # version is published
)
```

- Django's own `SlugField` validator accepts capitals and underscores. FR-015 asks for lowercase
  letters, digits and hyphens, and the URL converter matches only that, so the extra validator is
  what keeps the admin from saving a slug no address can reach.
- The validator runs on `full_clean()`, which the admin calls. Code writing through the ORM is not
  validated, the same as every other field in the package (Django's normal behaviour). A slug no
  address matches then answers "not found", which is safe.

**Freezing (US-4).** A document is *fixed* once any of its versions is published.

- `Document.save()`: when the row exists and `slug` differs from the stored value and
  `self.versions.published().exists()`, raise `PublishedVersionError` with
  `_("A document's slug cannot be changed once a version of it has been published.")`. The
  comparison reads the stored slug with one `values_list` query and only when the instance has a
  primary key, so creating a document costs nothing extra.
- `DocumentQuerySet.update(**kwargs)`: when `"slug" in kwargs` and
  `self.filter(versions__status__in=[CURRENT, SUPERSEDED]).exists()`, raise the same error. This
  covers `bulk_update()`, which calls `update()`.
- The name stays editable in every state (FR-017).

`PublishedVersionError` is reused rather than a new exception: the thing refused is a change to
published content, which is what that exception already names, and a caller catching it for one
case should catch it for the other.

**Admin (US-4).** `DocumentAdmin`:

- `prepopulated_fields = {"slug": ("name",)}` (FR-016).
- `get_readonly_fields(request, obj)` adds `"slug"` when `obj` has a published version.
- `get_prepopulated_fields(request, obj)` returns `{}` in the same case. Django's `AdminForm`
  indexes the form by every prepopulated field name, and a read-only field is not on the form, so
  leaving it in raises `KeyError` (research R3).

### Addresses

`mvp_compliance/urls.py`:

```python
class VersionNumberConverter:
    regex = r"[0-9]{4}\.[0-9]+"
    def to_python(self, value): return value
    def to_url(self, value): return value

register_converter(VersionNumberConverter, "version_number")

app_name = "mvp_compliance"
urlpatterns = [
    path("", DocumentIndexView.as_view(), name="index"),
    path("<slug:slug>/", DocumentView.as_view(), name="document"),
    path("<slug:slug>/versions/", VersionListView.as_view(), name="versions"),
    path("<slug:slug>/<version_number:number>/", VersionView.as_view(), name="version"),
]
```

A host project mounts it with `path("legal/", include("mvp_compliance.urls"))` and links with
`{% url 'mvp_compliance:document' 'privacy-policy' %}`. That is SC-007: one line in the URLs, one
link in a template. `versions` never collides with a number, because a number starts with four
digits.

### Querysets

- `DocumentQuerySet.in_force()`: documents with a current version, each carrying it on
  `current_versions` through `Prefetch("versions", queryset=Version.objects.current(),
  to_attr="current_versions")`. The index and the document's page both start here, so a document
  with only drafts is absent from both (FR-007).
- `VersionQuerySet.with_replaced_at()`: annotates `replaced_at`, the `published_at` of the earliest
  published version of the same document published after this one, through a `Subquery` ordered by
  `published_at`. `None` for the version in force. One query for any number of versions, which is
  SC-006 for the version list. The version's page uses the same annotation, so "in force from … to …"
  has one definition.

`Document.current` (existing) is left alone. The views read `current_versions[0]`.

### Views (`mvp_compliance/views.py`)

All four are readable by anyone: no login or permission mixin (FR-005). None offers a CRUD link:
`directory = []` on each detail view. Each sets `template_name` explicitly, so the page it renders is
never an mvp default, and each sets its breadcrumbs.

| View | Base | Object and 404 rule | Template | Page title / subtitle |
|---|---|---|---|---|
| `DocumentIndexView` | `MVPTemplateView` | `documents`: `Document.objects.in_force().order_by("name")` | `mvp_compliance/document_index.html` | "Legal documents" |
| `DocumentView` | `MVPDetailView` | `Document.objects.in_force()` by `slug`, 404 otherwise | `mvp_compliance/document_detail.html` | document name / "Version N, in force since D" |
| `VersionListView` | `MVPDetailView` | same queryset as `DocumentView`; `versions`: `document.versions.published().with_replaced_at().order_by("-published_at")` | `mvp_compliance/version_list.html` | "Versions of NAME" |
| `VersionView` | `MVPDetailView` | `Version.objects.published().with_replaced_at().select_related("document")` filtered by `document__slug` and `number`, 404 otherwise | `mvp_compliance/version_detail.html` | document name / "Version N" |

- A slug naming no document, a document with only drafts, and a number from another document all
  come back from `get_object()` as `Http404`. Being signed in, or staff, changes nothing (FR-007,
  US-1 scenario 8).
- Breadcrumbs: index → document → (versions | version). The index crumb links to
  `mvp_compliance:index`, so it resolves under whatever prefix the project chose.
- What each view overrides, checked against the resolved mvp 0.24.0 (design review):
  - All three detail views override `get_breadcrumbs()`. mvp's `PageObjectMixin.get_breadcrumbs()`
    builds its own trail and never reads a `breadcrumbs` attribute, so setting one is silently
    ignored and the default draws a crumb with an empty link. The index view overrides it too,
    because its link needs `reverse()`.
  - `DocumentView`: `get_queryset()` is `in_force()`; `get_context_data()` adds `version`
    (`self.object.current_versions[0]`); `get_page_title()` is the name; `get_page_subtitle()`
    builds "Version N, in force since D" with `_()` and `django.utils.formats.date_format`.
  - `VersionListView`: the same queryset; `get_context_data()` adds `versions`;
    `get_page_title()` is `_("Versions of %(name)s")`.
  - `VersionView`: overrides `get_object()` entirely. Django's `SingleObjectMixin.get_object()`
    filters on `slug`, which `Version` does not have, so the default raises `FieldError`. It
    filters `document__slug` and `number` and raises `Http404` when nothing matches. It also
    overrides `get_page_title()` (the default is `str(version)`, "Name #2026.1") and
    `get_page_subtitle()`.
  - `DocumentIndexView`: `get_context_data()` adds `documents`; `page_title` is a lazy string.
- mvp's title component writes the title and subtitle through autoescaped variables, so a document
  name with markup in it is escaped (checked in `cotton/page/title.html`).

### Templates (`mvp_compliance/templates/mvp_compliance/`)

Each extends `page_view.html` (the packaged mvp page) and fills `page.content`, nothing else. That is
what puts them in the shell with no project template (FR-012), and what a project replaces by placing
a template at the same path (FR-018).

- `document_detail.html`: a line with the version number and the date it came into force, linking
  to the version list ("Earlier versions"), then the wording in `<div class="prose max-w-none">`,
  written as `{{ version.html|safe }}`. `prose` ships in mvp's stylesheet (research R2).
- `version_detail.html`: the same wording block. Above it, for the version in force, "This is the
  version in force"; for a superseded one, an alert saying it has been replaced, the dates it was in
  force, and a link to the document's page ("Read the version in force").
- `version_list.html`: one row per version, newest first: number linking to the version's page,
  in force from, replaced on (or "In force" for the current one).
- `document_index.html`: one entry per document linking to its page. With none, a sentence saying
  nothing has been published yet (US-3 scenario 6).

Use mvp components (`c-card`, `c-alert` and so on) where one fits, checked against mvp's
`docs/components.md`. Only classes that ship in the prebuilt stylesheet: logical forms (`ps-`,
`me-`, `text-start`), never `pl-`/`mr-`/`text-left`. Dates through Django's `date` filter with no
format argument, so the project's `DATE_FORMAT` and the active language apply.

### Demo and test projects

The package adds nothing to menus (FR-014). The demo, as a host project, does:

- `demo/settings.py`: `FLEX_MENUS` renderers (`sidebar`, `dock`) and a minimal `MVP_CONFIG` sidebar
  title, which mvp's shell needs before any page renders (research R1).
- `demo/menus.py`: an `AppMenu` entry "Legal documents" pointing at `mvp_compliance:index`, added
  with the index in US-3.
- `demo/urls.py`: `path("legal/", include("mvp_compliance.urls"))`.
- `seed_demo`: every seeded document gets a slug (`privacy-policy`, `terms-of-use`,
  `cookie-policy`, `acceptable-use`), so the four states the walkthrough needs exist: two versions
  one superseded, one version, draft only, nothing at all.
- `demo/templates/demo/landing.html`: "There are no public pages yet" becomes a link to the index.

`tests/settings.py` gains the same `FLEX_MENUS` renderers, and `tests/urls.py` mounts the package
under `legal/`.

### Documentation

- `docs/pages.md` (new): mounting the addresses, the four URL names and their arguments, linking to
  a document from a footer, what each page shows and when it answers "not found", every template
  path with the context it receives, overriding one. Linked from the README.
- `docs/models.md`: the slug and when it is fixed. `in_force()` and `with_replaced_at()`.
- `docs/authoring.md`: choosing a slug in the admin, and that it is fixed at first publication.
- `CONTEXT.md`: **Slug** (FR-022).
- `CHANGELOG.md` `[Unreleased]`: Added entries for the pages and the slug.

## Stories and order

The stories run in sequence on one branch: **US-1, US-2, US-3, US-4**. US-1 introduces the slug
field and the URL module because the first page needs both. US-4 then fixes the slug and adds the
override proof and the template documentation, once all four templates exist.

| Order | Story | Touches |
|---|---|---|
| 1 | US-1 Reading the document in force | `models.py` (`slug`, `in_force()`), migration `0007`, `urls.py` (new), `views.py` (new, `DocumentView`), `document_detail.html`, `tests/settings.py`, `tests/urls.py`, `tests/factories.py`, demo settings, menu, URLs, seed and landing, `docs/pages.md` (new), `docs/models.md`, README, CHANGELOG, `en` catalog |
| 2 | US-2 Reading any version at its own address | `models.py` (`with_replaced_at()`), `urls.py` (converter, `version`), `views.py` (`VersionView`), `version_detail.html`, `docs/pages.md`, `docs/models.md`, `en` catalog |
| 3 | US-3 Finding a document and its earlier versions | `views.py` (`VersionListView`, `DocumentIndexView`), `urls.py`, two templates, `document_detail.html` (the link), `docs/pages.md`, `en` catalog |
| 4 | US-4 A stable address, and a project's own presentation | `models.py` (validator, freeze), `admin.py`, `tests/templates/` override, `docs/pages.md` (overriding), `docs/models.md`, `docs/authoring.md`, `CONTEXT.md`, CHANGELOG, `en` catalog |

## Complexity Tracking

| Addition | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| A path converter for version numbers | `2026.2` contains a dot, which `slug` rejects, and `str` would also match `versions` | `re_path` would work, but a named converter keeps all four patterns in one readable style and states the number's shape once |
| `with_replaced_at()` annotation | FR-003 and FR-010 need the date a version was replaced, which no field stores | Walking the list in Python works for the list page but not the single version's page, and two definitions of "replaced" can disagree |
| A lowercase validator beside `SlugField`'s own | FR-015; the converter matches only lowercase | `SlugField` alone accepts `Privacy_Policy`, which the admin would save and no address could reach |

## Outside this plan

Asking anyone to agree (R4), enforcement (R5), translations of a document (R7), the users' email
(#42), and any sitemap, `robots` or caching header. None of them is asked for, and each has its own
item.
