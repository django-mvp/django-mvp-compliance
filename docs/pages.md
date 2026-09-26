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

| URL name | Arguments | Address |
|---|---|---|
| `mvp_compliance:document` | `slug` | `<prefix>/<slug>/` |

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

## When the page is "not found"

The page answers 404, to every visitor whether signed in, staff or anonymous, when:

- no document has that slug, or
- the document has no version in force, because it has no versions or only drafts.

Nothing on the page links to editing or deleting a document. That is done in the admin.

## Overriding the template

The page renders `mvp_compliance/document_detail.html`. Put a template at the same path
in your project and it replaces the package's. It receives `document` (the object),
`version` (the version in force) and django-mvp's `page` context.
