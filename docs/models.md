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

Nothing about immutability or rendering is here yet: a published version's wording
can still be changed by this story's code. That lands in a later story on top of the
model above.
