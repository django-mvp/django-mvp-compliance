# Data model

The foundation everything else in this package sits on: a document with a lasting
identity, and the sequence of versions underneath it.

## `Document`

A named legal text — a privacy policy, a set of terms, a cookie policy. It has a
lasting identity and a unique `name`, and it holds no wording of its own: every word
lives in one of its versions.

```python
from mvp_compliance.models import Document

privacy = Document.objects.create(name="Privacy policy")
```

## `Version`

One revision of a document, holding the Markdown its author wrote.

```python
from mvp_compliance.models import Version

Version.objects.create(document=privacy, markdown="# Privacy policy\n\n...")
```

A version belongs to exactly one document, through `Version.document`, and a
document's versions come back through `document.versions.all()` in the order they
were added. `Version.number` is assigned automatically as one more than the highest
number its document already holds — it is never supplied by whoever writes the
version, and the database refuses a second version with a number its document
already has.

### Publishing

A version starts as a **draft**: no legal standing, invisible to readers, freely
editable and freely discardable.

```python
version = Version.objects.create(document=privacy, markdown="# Privacy policy\n\n...")
version.status  # Version.Status.DRAFT
version.is_published  # False
```

Calling `version.publish()` makes it the version **current** for its document — the
one in force — and moves whichever version was current before it to **superseded**.
A document has at most one current version at any moment, held by a database
constraint rather than by the method:

```python
version.publish()
version.status  # Version.Status.CURRENT
version.published_at  # the moment it was published
```

Publishing an already-published version raises `mvp_compliance.exceptions.PublishError`
and changes nothing about the document. Publishing is one-way: the package offers no
`unpublish`, `revert`, `rollback`, `restore` or `make_current` — a correction of any
size is published again as a new version.

### Immutability

Once a version is published — current or superseded, `version.is_published` — its
`document`, `number`, `markdown` and `published_at` can never change again. Only
`status` can, because moving from current to superseded is the one change a
published version ever undergoes:

```python
version.markdown = "Revised wording"
version.save()  # raises PublishedVersionError; the stored wording is untouched

Version.objects.filter(pk=version.pk).update(markdown="Revised wording")  # same
Version.objects.bulk_update([version], ["markdown"])  # same
version.delete()  # raises PublishedVersionError; a published version can't be deleted
Version.objects.filter(pk=version.pk).delete()  # same
```

A draft is unaffected by any of this: it stays freely editable and freely
discardable until the moment it is published. A correction, of any size, is always
a new version — never an edit to the one that carries the error, which stays
readable at its own standing.

Deleting a `Document` that still holds any version — draft, current or superseded —
raises `django.db.models.ProtectedError` and leaves the document in place; a
document holding none deletes normally. This is `Version.document`'s
`on_delete=PROTECT`, enforced by Django's deletion collector on every route,
including a queryset delete and a cascade from elsewhere — the package adds no
override on either side.

`mvp_compliance.exceptions.PublishedVersionError` is what every route above raises.
Rendering is not here yet: `Version.html` and the renderer land in a later story.
