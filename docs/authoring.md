# Writing and publishing a document

Documents live in the database rather than in the codebase so that changing one needs no
engineer, no pull request and no deployment. This is the surface that makes that true: the
Django admin, under **Compliance**.

Whoever is responsible for the wording is not assumed to be a developer, to be an employee, or
to know Markdown.

## The editor

`MarkdownEditorWidget` turns the version's `markdown` field into an editor with formatting
controls, so no syntax has to be typed. It offers seven of them and nothing else:

- a heading control that steps through the heading levels
- bold and italic
- bulleted and numbered lists
- links
- block quotes

There is no control for an image, an embed, a table, a tag or raw HTML. A legal document is
structured prose, and every control offered is one somebody has to be supported in using.

What gets stored is ordinary Markdown either way, so an author who prefers to type it is not
obstructed:

```python
from mvp_compliance.models import Document, Version

privacy = Document.objects.get(name="Privacy policy")
Version.objects.create(document=privacy, markdown="## What we collect\n\nYour email address.")
```

The toolbar is declared on the widget and travels to the page as data. Every control it offers
survives the sanitiser the package applies at publication, and a test asserts that in both
directions — each control's output survives, and content outside the allow list is removed — so
no button can produce something publication would silently strip.

### Changing what the editor offers

Subclass the widget, change `TOOLBAR`, and point the form at your subclass. A control added
there needs a matching icon rule in `markdown-editor.css`, because the editor library ships no
icons of its own.

Adding a control whose output the sanitiser removes is the mistake worth guarding against. If
you widen the toolbar, widen `MarkdownRenderer.allowed_tags` to match, or the extra button
produces wording that vanishes at publication.

## The form

`VersionForm` is what the admin posts. It exposes exactly two fields, `document` and
`markdown`, because those are the only two an author supplies.

The `html` a reader is served is produced once by `Version.publish()` and is the record of what
somebody was shown, so it is never something a form can write. `number`, `status` and
`published_at` belong to the package for the same reason.

## Reading it back before publishing

Publishing cannot be undone, so the last look before it has to be accurate.

Each version has a preview at its own address in the admin, linked from the version's page. It
shows the rendering a reader will be served — produced by the same rendering publication uses,
not by the editor's own inline display.

The distinction matters and the page says so on its face. The editor renders formatting as you
type, which helps while writing, and it knows nothing about the sanitiser. The preview is the
real output. Content the allow list removes is shown removed, so the loss is visible before
publication rather than discovered afterwards, when it cannot be corrected.

A preview shows what is **stored**, not what is currently in the editor. Save, then preview.
That way what the preview showed and what publication stores cannot disagree.

For a version that has already been published, the preview shows the HTML stored on the row
rather than rendering it again, because that stored output is the evidence of what a person was
shown. Upgrading the Markdown library or changing the allow list does not alter it.

## Who can do what

Reaching any of this needs the permissions on `Version` that Django creates — `view_version`
and `change_version` for reading and writing, `add_version` to start one. A request without
them reaches nothing at any address the package serves, and a document with no published
version is invisible to a visitor.

See [Permissions](../README.md#permissions) in the README for the publishing permission, which
is deliberately separate.
