# Implementation Plan: Writing and publishing a document without a developer

**Branch**: `002-writing-and-publishing` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-writing-and-publishing/spec.md`

## Summary

The Django admin, and nothing else. FS-001 built the documents, the versions and the one-way
publish; this feature is the surface a person uses to reach them.

`VersionAdmin` serves the editor: a textarea carrying EasyMDE, whose toolbar is declared here as
exactly six controls — headings, bold, italics, lists, links, block quotes — so that the set the
specification forbids does not exist rather than being hidden. The value stored is ordinary
Markdown, so somebody who prefers to type it is not obstructed.

Two extra admin addresses hang off that model admin. The preview renders the version's stored
Markdown through `get_renderer()` — the same call `Version.publish()` makes — so what an author
approves is what publication will store, and content the allow list strips is shown stripped. The
publish page is a confirmation step behind its own model permission, `publish_version`, which says
in plain words that the wording cannot be changed afterwards and that a correction means another
version. Both refusals FS-001 raises arrive as admin messages an author can act on rather than as a
traceback.

Once a version is published, `has_change_permission()` returns `False` for it, which puts Django's
own read-only page in front of the author: values as text, no inputs, no save. Starting the next
version is a link on the document's page that opens the add form with the wording in force already
in the box.

The demo project gains the admin, three seeded accounts and a document in every state, so the whole
of it can be used rather than read about.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.14)

**Primary Dependencies**: Django 5.2 and 6.0, django-mvp 0.23.0. No new Python dependency.

**Vendored assets added here**: EasyMDE 2.21.0 (`easymde.min.js`, `easymde.min.css`, MIT).
Article VII and Article II justification in `research.md` R2–R4 and in Complexity Tracking below.

**Storage**: no new table. One migration, adding the `publish_version` permission to `Version`.

**Testing**: pytest with pytest-django, `tests/settings.py`, an in-memory SQLite database. Admin
pages exercised through the `client` fixture against real users with real permissions, never by
calling a `ModelAdmin` method directly.

**Target Platform**: a Django project that has installed django-mvp and enabled
`django.contrib.admin`.

**Project Type**: installable Django application. This feature is its authoring surface.

**Constraints**: Article XII (publishing stays one-way — this surface calls `publish()` and never
reaches past it), Article XIII (the preview and publication share one renderer, and nothing
re-renders a published version), Article XIV (no string anywhere claims compliance), Article VIII
(every string translatable, templates included).

**Scale/Scope**: two model admins, one widget, one form, two admin views, four templates, two
static files of our own and two vendored, five user stories, 22 functional requirements.

## Constitution Check

Read before planning and re-checked after the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every requirement is reachable through an HTTP request, which is the easiest kind of failing test to write first. The permission requirements are one test per role per address | Pass |
| II Simplicity | Two model admins, one widget, one form, two views. No editor abstraction, no registry of toolbars, no base admin class | Pass |
| III Anti-Abstraction | `MarkdownEditorWidget` is one concrete widget, not a base class awaiting a second. The toolbar is a list on it, not a plugin system | Pass |
| IV Integration-First | Every acceptance scenario is exercised the way a compliance editor touches it — a signed-in user with a permission set, requesting an address | Pass |
| V Security and data-safety | The preview writes sanitised HTML into the page and nothing else; both admin views are wrapped in `admin_view` and check a model permission of their own; publishing is POST-only behind CSRF | Pass |
| VI Documentation | README gains the authoring surface, the permission and the widget; CHANGELOG gains an Added entry; `CONTEXT.md` gains **Compliance editor** | Pass |
| VII Dependency discipline | No Python dependency added. Two vendored JavaScript assets, justified in Complexity Tracking | Pass, with Complexity Tracking |
| VIII Internationalization | Every admin label, message, button and template string wrapped with `gettext_lazy` or `{% translate %}`; the `en` catalog regenerated | Pass |
| IX Data-model conventions | No field added. The one model change is `Meta.permissions`, which indexes nothing | Pass |
| X Test structure and fixtures | `tests/test_admin.py`, `tests/test_widgets.py`, `tests/test_forms.py` mirror the new modules. User fixtures wrap a single `UserFactory`; permission sets are call-site overrides, never factory subclasses | Pass |
| XI Cohesion (Python) | Both admin views are `ModelAdmin` methods, where Django owns the grouping. The toolbar and its icon names live on the widget class | Pass |
| XII Published version immutable | This surface never writes to a published row: the publish page calls `Version.publish()` and the change page is read-only past publication. The model guards stay the enforcement; the admin is a second, softer layer | Pass |
| XIII Rendered output is the evidence | The preview calls `get_renderer()` — the same resolver `publish()` uses — and reads stored HTML for a version that has been published. No admin path re-renders a published version | Pass |
| XIV Mechanics, never compliance | FR-019 has a test of its own: every user-facing string this feature ships is swept for a compliance claim | Pass |
| XV Personal data minimal | This feature stores nothing about a person. It reads `request.user` for permission checks and records none of it | Pass |
| XVI Compatibility | Pre-1.0. The permission is added, nothing changes shape, and no stored row is rewritten | Pass |

## Project Structure

### Documentation (this feature)

```text
specs/002-writing-and-publishing/
├── spec.md              # merged to main at the spec gate
├── decisions.md         # merged with it; appended to here
├── plan.md              # this file
├── research.md          # what had to be settled first
├── tasks.md             # the task graph
├── progress.md          # run narrative
└── feature-state.json   # the ledger
```

No `contracts/`: the contract is a set of admin addresses and the test suite states it. No
`data-model.md`: the only model change is one permission line.

### Source code

```text
mvp_compliance/
├── admin.py                     # DocumentAdmin, VersionAdmin, preview and publish views
├── forms.py                     # VersionForm — the editor widget on `markdown`
├── widgets.py                   # MarkdownEditorWidget — the toolbar declaration and its Media
├── models.py                    # unchanged but for Version.Meta.permissions
├── migrations/
│   └── 0002_version_publish_permission.py
├── templates/admin/mvp_compliance/version/
│   ├── preview.html             # the rendering the public will be served
│   ├── publish_confirmation.html
│   └── change_form.html         # adds the Preview and Publish links to the object tools
├── templates/admin/mvp_compliance/document/
│   └── change_form.html         # adds the Start the next version link
├── static/mvp_compliance/
│   ├── markdown-editor.css      # the six toolbar icons, and fitting the control to the admin
│   ├── markdown-editor.js       # instantiates EasyMDE against the declared toolbar
│   └── vendor/easymde/
│       ├── easymde.min.js       # 2.21.0, unmodified
│       ├── easymde.min.css      # 2.21.0, unmodified
│       ├── LICENSE              # MIT, upstream
│       └── VERSION.md           # version, source URL, SHA-256 of each file
└── locale/en/LC_MESSAGES/
    └── django.po                # regenerated

tests/
├── conftest.py                  # user fixtures by permission set, alongside the existing ones
├── factories.py                 # UserFactory added
├── test_admin.py                # TestVersionAdmin, TestPreview, TestPublish, TestDocumentAdmin,
│                                # TestDraftPrivacy, TestUserFacingStrings
├── test_widgets.py              # TestMarkdownEditorWidget
├── test_forms.py                # TestVersionForm
└── test_app.py                  # D11: narrowed to "no public URLs"

demo/
├── settings.py                  # admin mounted
├── urls.py                      # admin/ added
├── templates/demo/landing.html  # points at the admin
└── management/commands/seed_demo.py   # accounts and a document in every state
```

## Design

### The editor (US-1)

`MarkdownEditorWidget` subclasses `forms.Textarea`. It carries:

- a `Media` inner class naming the two vendored files and the two of our own, in that order;
- `TOOLBAR`, the declaration of what exists — `heading`, `bold`, `italic`, `unordered-list`,
  `ordered-list`, `link`, `quote`, with separators. Nothing else. Not image, not table, not
  horizontal rule, not code, not strikethrough, and none of the preview toggles
  (`research.md` R6);
- a `data-mvp-compliance-markdown-editor` attribute and the serialised toolbar in a `data-toolbar`
  attribute, which `markdown-editor.js` reads.

The toolbar is declared in Python and travels to the page as data, so FR-003 is checkable by
requesting the page and reading what was served rather than by importing a module and inspecting an
attribute.

Each button gets a `className` of the form `mvp-compliance-toolbar-<name>`, and
`markdown-editor.css` draws the icon as an inline SVG background on that class. EasyMDE's own
Font Awesome class names are not used and Font Awesome is not shipped (`research.md` R3).

`VersionForm` puts the widget on `markdown` and is `VersionAdmin.form`.

**Agreement with the allow list (FR-004)** is a test, not a promise: one Markdown sample per
toolbar control, each rendered through `MarkdownRenderer`, each asserted to keep the element it
produces. A control whose output the renderer strips fails there.

### Drafts stay private (US-2)

Everything this feature serves sits under the admin, and Django refuses a request that is not from
a signed-in staff account before any view of ours runs. On top of that:

- the change, add and changelist pages use Django's own `view` and `change` permissions on
  `Version`;
- the preview checks `has_view_permission`;
- the publish page checks `mvp_compliance.publish_version`.

The test walks every address the feature serves against four callers — anonymous, a signed-in
non-staff user, a staff user with no `mvp_compliance` permissions, and a staff user with them — and
asserts the first three reach nothing. FR-008 needs no code: the package still registers no public
URLs, and `tests/test_app.py` keeps saying so.

Discarding a draft is Django's delete, which `Version.delete()` already refuses for a published
row. `VersionAdmin.has_delete_permission()` returns `False` for a published object so the admin
does not offer an action that would raise.

### Preview (US-3)

`VersionAdmin.get_urls()` adds `<pk>/preview/`, named `admin:mvp_compliance_version_preview`. It
renders `preview.html` with the output of `get_renderer()().render(version.markdown)` for a draft,
and with the stored `html` for a version that has been published, because Article XIII forbids
re-rendering one.

The page states in its own heading that this is what a reader will be served, so the distinction the
specification draws between it and the editor's inline display is on the screen and not only in the
specification (US-3 scenario 5).

SC-004 gets a direct test: preview a draft, capture the rendered HTML from the response, publish it,
and assert the stored `html` is identical.

### Publishing (US-4)

`<pk>/publish/`, named `admin:mvp_compliance_version_publish`.

- GET renders the confirmation, which names the document and version, shows the rendering that is
  about to go live, and states that the wording cannot be changed afterwards and that a correction
  means another version.
- POST calls `Version.publish()`. `PublishError` and `PublishedVersionError` are caught and
  rendered as `messages.error` on the redirect back to the change page (FR-018) — the exception's
  own message, which FS-001 already wrote as a sentence for a person.
- Both verbs require `mvp_compliance.publish_version`. Without it the response is a 403, and the
  link is not rendered on the change page at all.
- Declining is the absence of a POST: the confirmation page's other control is a link back, and
  nothing is written (FR-016).

Saving a draft never publishes. There is no `publish` field, no checkbox and no changelist action —
the only route is this page (FR-013), and a test asserts that saving the change form with every
field filled leaves the status a draft.

For a published version, `has_change_permission(request, obj)` returns `False`, so Django serves its
read-only page (`research.md` R7).

### Starting from the wording in force (US-5)

`DocumentAdmin`'s change form adds a link reading **Start the next version**, pointing at the
version add page with the document in the query string.

`VersionAdmin.get_changeform_initial_data()` reads that parameter and, when the named document has
a version in force, returns its `markdown` as the initial value alongside the document. With no
version in force it returns the document alone and the box is empty, which is the ordinary case for
a new document (US-5 scenario 3).

Nothing is copied on the server: the initial value populates a form, and the published version it
came from is never opened for writing (FR-022, and the model would refuse anyway).

### No claim of compliance (FR-019)

One test collects every user-facing string this feature ships — the admin labels, the widget, the
templates' translatable strings and the message catalog — and asserts none of them claims a site is
compliant with anything. It runs over the shipped catalog rather than over a hand-kept list, so a
string added later is covered without anybody remembering to add it.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| 340 KB of vendored JavaScript (EasyMDE 2.21.0) | FR-002 requires formatting controls, and US-3 scenario 5 presupposes an editor that renders formatting inline. Neither is reachable with a plain textarea | A hand-written toolbar over a textarea has no inline display, so the specification's own comparison would have nothing to compare; a content delivery network hands a third party script execution inside an authenticated admin session (`research.md` R4); a Python wrapper package adds a dependency and a second opinion about the toolbar in exchange for the same two files |
| Six inline SVG icons in our own stylesheet | EasyMDE ships no icons and expects Font Awesome 4 class names (`research.md` R3) | Shipping a whole icon font for six buttons, when nothing else in the package uses one |
| `admin.py`, `forms.py` and `widgets.py` appear where FS-001's D5 said none would | FS-001 scoped itself to the model layer and named this feature as where the surface arrives. The supersession is recorded as D11 in `decisions.md` | Nothing simpler exists: the specification's surface is the Django admin |
