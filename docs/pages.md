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
| `mvp_compliance:document` | `slug` | `<prefix>/<slug>/` | `mvp_compliance.views.DocumentView` |

There is one page per document: its address always shows the version in force. The same
address with `?version=<number>` shows that published version, current or superseded,
for as long as it stays published — a number such as `2026.1` or `2026.12`. A `?version=`
value that names no published version of the document is "not found".

The slug is the document's `slug` field, so `Document(slug="privacy-policy")` is served
at `legal/privacy-policy/` under the mount above. Link to it from a footer, or anywhere
else in a template:

```html
<a href="{% url 'mvp_compliance:document' 'privacy-policy' %}">Privacy policy</a>
```

An impressum is linked the same way, from the footer of the site, wherever the law of your
country expects to find it:

```html
<a href="{% url 'mvp_compliance:document' 'impressum' %}">Impressum</a>
```

## What a visitor sees

The page shows the document's name, a line under it, and the wording of the version
shown: the version in force by default, or the one named by `?version=`. When a new
version is published, the plain address shows it at once; an earlier `?version=` address
keeps showing what it always showed.

On wide screens the page is two columns. The left column is a card titled "Documents" that
lists every document with a version in force, alphabetically, each linking to its own page,
with the one being shown marked. The right column holds the document's name, the version
switcher and the wording. On a narrow screen the card stacks above the document. A document
with only drafts, or with no versions, is left out. The list is the same on a `?version=`
address as on the plain one.

The card stays in view while a long document scrolls. It stops below the shell's top bar,
at an offset the package's stylesheet, `mvp_compliance/pages.css`, sets to `5rem`. If your
project's top bar is a different height, set the custom property in your own stylesheet:

```css
:root {
  --mvp-compliance-header-clearance: 6rem;
}
```

The line under the name reads `v2026.1 - 26 September 2026`: the shown version's
number and the day it was published, in the project's date format. When the signed-in
visitor has accepted that version it continues `· Agreed on 27 September 2026`, with the
date of their acceptance. An anonymous visitor, and someone who has accepted a different
version of the document but not this one, see the first part only.

A notice, such as an impressum, is read and never accepted, so its line is the first part
only for everybody: no `Agreed on`, even for a signed-in visitor who accepted the document
before it became a notice, and on an earlier `?version=` address as on the plain one. The
rest of the page is the same as any document's, and the list beside the wording names it
along with the documents people agree to.

The page builds this line with `mvp_compliance.views.VersionSubtitleMixin`. A project
view that shows a version and wants the same line mixes it in ahead of the django-mvp
detail view and defines `get_version()`.

The wording is the `html` stored on the version when it was published, written out
as it is stored. Nothing renders Markdown while the page is served. That HTML is what the
configured renderer produced and sanitised at publication, so a project that points
`MVP_COMPLIANCE_RENDERER` at a renderer with a looser allow list serves that looseness on
its own pages.

## The menu

The package adds nothing to your menus: which pages appear in navigation is your
decision. A host project adds its own entry, as the demo does in `demo/menus.py`, here
pointing at one document's page:

```python
from django.urls import reverse_lazy
from flex_menu import MenuItem
from mvp.menus import AppMenu

AppMenu.append(
    MenuItem(
        name="legal-documents",
        url=reverse_lazy("mvp_compliance:document", args=["privacy-policy"]),
        extra_context={"label": "Legal documents", "icon": "file-earmark-text"},
    )
)
```

Every page's breadcrumbs are the document's name alone. A `?version=` address shows the
same trail as the plain one.

## The version switcher

Every document page carries a version switcher among its actions: a primary button,
labelled with the version shown and a dropdown caret, listing every published version of
the document, newest first, each as `v2026.1 - 26 September 2026` linking to the same
page with `?version=` and that number. The version shown is marked. The switcher is there
even when the document has only one published version, and drafts are never listed.

## A superseded version

When `?version=` shows a version that is no longer in force, the page carries one alert
row above the wording: a notice that the version was replaced, the date it came into
force and the date it was replaced, and a "View current version" button leading to the
document's plain address, which always shows the version now in force. The version in
force shows no such alert, whether it is reached with no parameter or with its own number
as `?version=`.

## When the page is "not found"

The page answers 404, to every visitor whether signed in, staff or anonymous, when:

- no document has that slug,
- the document has no version in force, because it has no versions or only drafts, or
- `?version=` names a value that is not a published version of the document — a draft's
  number (a draft has none), another document's number, or anything else.

Nothing on the page links to editing or deleting a document. That is done in the admin.

## Overriding a template

Every page is one template under `mvp_compliance/`, and each extends django-mvp's
`page_view.html` and fills only its `page.content` and, where it has one, `page.actions`
block. To restyle a page, place a template at the same path in your project. Django finds
yours first, and the package's is never used for that page. The package needs no other
change, and you do not fork it.

| Template path | Page | Receives |
|---|---|---|
| `mvp_compliance/document_detail.html` | `mvp_compliance:document` | `document`, `version`, the version shown, carrying `replaced_at`: the date the next version was published, or `None` for the version in force, and `versions`, every published version of the document newest first, and `documents`, every document that has a version in force in name order |

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
