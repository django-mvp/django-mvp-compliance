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

Nothing about publishing, immutability or rendering is here yet: a version at this
stage is freely editable Markdown with no legal standing. Those behaviours land in
later stories on top of the two models above.
