# Pages

Each document that has a version in force is readable as a page of your site, in the
django-mvp shell, at an address that does not change when a new version is published.
Anyone can read it, signed in or not.

## Mounting the addresses

Include the package's URLs under a prefix of your choosing:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("legal/", include("mvp_compliance.urls")),
]
```

The pages render inside the shell, and the shell needs the menu renderers django-mvp
documents for its install. Without `FLEX_MENUS` in your settings, rendering any
django-mvp page raises. The package adds nothing to your menus: which pages appear in
navigation is your decision.

## The address

| URL name | Arguments | Address | View |
|---|---|---|---|
| `mvp_compliance:index` | none | `<prefix>/` | `mvp_compliance.views.DocumentIndexView` |
| `mvp_compliance:document` | `slug` | `<prefix>/<slug>/` | `mvp_compliance.views.DocumentView` |
| `mvp_compliance:versions` | `slug` | `<prefix>/<slug>/versions/` | `mvp_compliance.views.VersionListView` |
| `mvp_compliance:version` | `slug`, `number` | `<prefix>/<slug>/<number>/` | `mvp_compliance.views.VersionView` |

The number is a version's own, such as `2026.1` or `2026.12`: four digits, a dot, then
digits. Anything else in that position, `2026` for example, is not a version address.
`versions` is not a number: `<prefix>/<slug>/versions/` is the list of the document's
versions.

The slug is the document's `slug` field, so `Document(slug="privacy-policy")` is served
at `legal/privacy-policy/` under the mount above. Link to it from a footer, or anywhere
else in a template:

```html
<a href="{% url 'mvp_compliance:document' 'privacy-policy' %}">Privacy policy</a>
```

## What a visitor sees

The page shows the document's name, a line under it, and the wording of the version in
force. When a new version is published, the same address shows it at once.

The line under the name reads `v2026.1 · published 26 September 2026`: the version's
number and the day it was published, in the project's date format. When the signed-in
visitor has accepted that version it continues `· Agreed on 27 September 2026`, with the
date of their acceptance. An anonymous visitor, and someone who has accepted a different
version of the document but not this one, see the first part only. A version's own page
shows the same line for that version.

Both pages build the line with `mvp_compliance.views.VersionSubtitleMixin`. A project
view that shows a version and wants the same line mixes it in ahead of the django-mvp
detail view and defines `get_version()`.

The wording is the `html` stored on the version when it was published, written out
as it is stored. Nothing renders Markdown while the page is served. That HTML is what the
configured renderer produced and sanitised at publication, so a project that points
`MVP_COMPLIANCE_RENDERER` at a renderer with a looser allow list serves that looseness on
its own pages.

## The index

`mvp_compliance:index`, at the mount's root, lists every document that has a version in
force, alphabetically, each linking to its page. A document with only drafts, or with no
versions, is left out. When nothing is in force it says "Nothing has been published yet."

A site that wants one "Legal" link in its footer points it at the index:

```html
<a href="{% url 'mvp_compliance:index' %}">Legal</a>
```

The package adds nothing to your menus. A host project adds its own entry, as the demo
does in `demo/menus.py`:

```python
from flex_menu import MenuItem
from mvp.menus import AppMenu

AppMenu.append(
    MenuItem(
        name="legal-documents",
        view_name="mvp_compliance:index",
        extra_context={"label": "Legal documents", "icon": "file-earmark-text"},
    )
)
```

Every page's breadcrumbs start with a "Legal documents" crumb linking to the index.

## Earlier versions

When a document has more than one published version, its page carries a "Previous
versions" dropdown in the page actions. It lists every earlier published version, newest
first, each as `v2026.1 · published 26 September 2026` linking to that version's page,
and ends with an "All versions" link to `mvp_compliance:versions`. A document with a
single published version has no dropdown. Drafts are never listed.

The list page, `mvp_compliance.views.VersionListView`, lists every published version of
the document, newest first: its number, linking to the version's page, the date it came
into force, and the date it was replaced, or "In force" for the version now in force.
Drafts are not listed. It answers 404 under the same conditions as the document's page.

## A version's own page

Every published version stays readable at its own address, which never changes and always
shows the wording that version was published with:

```html
<a href="{% url 'mvp_compliance:version' 'privacy-policy' '2026.1' %}">Version 2026.1</a>
```

Someone who agreed to wording that has since been replaced can open that exact version.
The page shows the document's name, the version's number and its wording, written out as
stored. What sits above the wording depends on where the version stands:

- **In force:** "This is the version in force.", with the same `v2026.1 · published D`
  line under the title that the document's page shows.
- **Replaced:** a notice that the version was replaced, the date it came into force and
  the date it was replaced, and a link to the document's page, which shows the version
  now in force. A version is replaced on the day the next version of the same document
  was published.

The version's page answers 404, to every visitor, when no document has that slug, when
that document has no published version with that number (a number that belongs to
another document included), or when the version is still a draft, since a draft has no
number.

## When the page is "not found"

The page answers 404, to every visitor whether signed in, staff or anonymous, when:

- no document has that slug, or
- the document has no version in force, because it has no versions or only drafts.

Nothing on the page links to editing or deleting a document. That is done in the admin.

## Overriding a template

Every page is one template under `mvp_compliance/`, and each extends django-mvp's
`page_view.html` and fills only its `page.content` block. To restyle a page, place a
template at the same path in your project. Django finds yours first, and the package's
is never used for that page. The package needs no other change, and you do not fork it.

| Template path | Page | Receives |
|---|---|---|
| `mvp_compliance/document_index.html` | `mvp_compliance:index` | `documents`, the documents in force in name order, each with its current version |
| `mvp_compliance/document_detail.html` | `mvp_compliance:document` | `document`, `version`, the version in force, and `previous_versions`, the other published versions newest first |
| `mvp_compliance/version_list.html` | `mvp_compliance:versions` | `document`, and `versions`, newest first, each carrying `replaced_at` |
| `mvp_compliance/version_detail.html` | `mvp_compliance:version` | `document`, and `version`, carrying `replaced_at`: the date the next version was published, or `None` for the version in force |

Every page also receives django-mvp's `page` context: its title and breadcrumbs.

A project's own `mvp_compliance/document_detail.html`, for example:

```html
{% extends "page_view.html" %}
{% block page.content %}
  <article class="prose max-w-none">{{ version.html|safe }}</article>
{% endblock page.content %}
```

`version.html` is the sanitised HTML stored at publication, so write it out with `|safe`
and render nothing else from Markdown. Put your template's directory in
`TEMPLATES["DIRS"]`, or in an app listed before `mvp_compliance` in `INSTALLED_APPS`.
Strings you add are yours to translate.
