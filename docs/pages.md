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
| `mvp_compliance:version` | `slug`, `number` | `<prefix>/<slug>/<number>/` | `mvp_compliance.views.VersionView` |

The number is a version's own, such as `2026.1` or `2026.12`: four digits, a dot, then
digits. Anything else in that position, `versions` or `2026` for example, is not a version
address.

The slug is the document's `slug` field, so `Document(slug="privacy-policy")` is served
at `legal/privacy-policy/` under the mount above. Link to it from a footer, or anywhere
else in a template:

```html
<a href="{% url 'mvp_compliance:document' 'privacy-policy' %}">Privacy policy</a>
```

## What a visitor sees

The page shows the document's name, the number of the version in force, the date it came
into force, and that version's wording. When a new version is published, the same
address shows it at once.

The wording is the `html` stored on the version when it was published, written out
as it is stored. Nothing renders Markdown while the page is served. That HTML is what the
configured renderer produced and sanitised at publication, so a project that points
`MVP_COMPLIANCE_RENDERER` at a renderer with a looser allow list serves that looseness on
its own pages.

## A version's own page

Every published version stays readable at its own address, which never changes and always
shows the wording that version was published with:

```html
<a href="{% url 'mvp_compliance:version' 'privacy-policy' '2026.1' %}">Version 2026.1</a>
```

Someone who agreed to wording that has since been replaced can open that exact version.
The page shows the document's name, the version's number and its wording, written out as
stored. What sits above the wording depends on where the version stands:

- **In force:** "This is the version in force.", with the same "Version N, in force
  since D" line under the title that the document's page shows.
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

## Overriding the template

The document's page renders `mvp_compliance/document_detail.html`. Put a template at the
same path in your project and it replaces the package's. It receives `document` (the
object), `version` (the version in force) and django-mvp's `page` context.

A version's page renders `mvp_compliance/version_detail.html`, replaced the same way. It
receives `document`, `version` (the object, carrying `replaced_at`: the date the next
version was published, or `None` for the version in force) and django-mvp's `page`
context.
