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
somebody was shown, so it is never something a form can write. `number`, `status`,
`published_at` and the publisher belong to the package for the same reason.

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

## Publishing

Publishing needs its own permission, `publish_version`, and its own step: a version's change
page offers a **Publish** link once it is a draft, to whoever holds it. There is no other route
— no changelist action, no field, no checkbox saves and publishes at once.

The link leads to a confirmation page before anything happens. It names the document and
version, shows the rendering about to go live, and says plainly that the wording cannot be
changed afterwards and that a correction is published as another version. Publishing happens
only when that page is posted. Following its **Back** link instead leaves the draft untouched.

Publishing records who did it: the account signed in when the confirmation is posted becomes the
version's publisher. A published version's page shows **Published by** beside **Published at**,
and both lists show it too — the version list for every version, the document list for the
version in force. If that account is later removed, the version says "An account since removed";
a version with nobody recorded says "No publisher recorded".

`Version.publish()` refuses a version that is not a draft, and one whose rendered output is
empty once whitespace is stripped. Both refusals reach the person publishing as a message on
the page they return to, not as a traceback.

Once a version is published, its change page in the admin offers nothing to edit. Its wording
and its publisher never change, and both are readable in full. Django serves its own read-only
page — not a form with disabled fields, and not one whose save is silently refused.

## Starting the next version from the one in force

Most rewordings are edits to what is already there rather than a rewrite from nothing, so a
version that is currently in force offers a **Start the next version** link on its own change
page, next to Preview. It opens the version add form with that document already chosen.

`VersionAdmin.get_changeform_initial_data()` reads the document named in the query string and,
when it has a version in force, hands that version's Markdown to the form as an initial value,
so the new draft opens with the current wording already in the box, ready to be edited. A
document with nothing published yet opens the box empty, which is the ordinary case for a new
document.

The version the wording came from is never opened for writing. The initial value populates a
new, unsaved form; nothing on the server writes to the version it was read from, and
`Version.save()` would refuse a write to a published row regardless.

A document's own change page offers **View current version**, leading to that page when one
exists, and **Version history**, leading to the versions list narrowed to this document with
`VersionAdmin.list_filter`.

## The documents list

Documents in the admin changelist are more than a list of names. Beside each one: the version in
force, linked to its own page, or a plain **No version in force** for a document that has never
published anything — the ordinary state for a new document, never treated as a gap. How long that
version has been in force. And how many versions the document has published — current and
superseded together, since both were once live, and a draft never counted, because a draft has no
legal standing to be one of them.

The list costs the same number of queries whether it shows one document or a hundred:
`DocumentAdmin.get_queryset()` annotates the published count once and fetches every version in
force in a single prefetch, rather than asking the database once per row.

A new version whose wording is identical to the one in force is refused **at publication**, not
when it is saved. Saving such a draft is harmless — it has no standing and can be edited or
thrown away. Publishing it is the act that would supersede a wording with its own copy.

Publication is also the only moment the question has a settled answer. A draft that duplicates
today's version in force is not a duplicate once somebody else publishes another one, so a draft
saved weeks ago is judged against whatever is in force when it goes live rather than against
whatever was in force when it was written.

The comparison ignores two differences neither of which a reader would see: the carriage returns
a browser stores with a text area's content, and a trailing newline. Restoring an earlier wording
is still allowed, because the comparison is against the version in force and nothing else — that
is how this package goes back to something a superseded version said.

The refusal reaches whoever is publishing as a message on the page they return to, alongside the
two `Version.publish()` already raises.

## Who can do what

Reaching any of this needs the permissions on `Version` that Django creates — `view_version`
and `change_version` for reading and writing, `add_version` to start one. A request without
them reaches nothing at any address the package serves, and a document with no published
version is invisible to a visitor.

A version can only be added from a document: `VersionAdmin.has_add_permission()` refuses a
request that names none, so the versions list offers no add control and a bare request for the
add form is refused regardless of `add_version`. Reaching the add form from a document, the way
both change pages above do, still works.

See [Permissions](../README.md#permissions) in the README for `publish_version`, which is
deliberately separate from the permissions above.
