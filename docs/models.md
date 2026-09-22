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

Calling `version.publish()` renders `version.markdown` to HTML, then makes the
version **current** for its document — the one in force — and moves whichever
version was current before it to **superseded**. A document has at most one
current version at any moment, held by a database constraint rather than by the
method:

```python
version.publish()
version.status  # Version.Status.CURRENT
version.published_at  # the moment it was published
version.html  # the HTML a reader is served, rendered from version.markdown
```

Publishing an already-published version raises `mvp_compliance.exceptions.PublishError`
and changes nothing about the document. The same applies when something else published
the version first and this copy of it is out of date, so a caller that catches
`PublishError` catches both. Publishing is also refused, before anything is written,
when the rendered output is empty once whitespace is stripped — a draft whose markdown
produces nothing has nothing to publish. Publishing is one-way: the
package offers no `unpublish`, `revert`, `rollback`, `restore` or `make_current` — a
correction of any size is published again as a new version.

### Rendering

`version.html` is produced once, at publication, by
`mvp_compliance.rendering.MarkdownRenderer` — never again on the way a stored
version is read, so a later change to the renderer cannot alter what a published
version already says:

```python
from mvp_compliance.rendering import MarkdownRenderer

MarkdownRenderer().render("# Heading\n\nSome *text* and a [link](https://example.com).")
```

The output is sanitised against an explicit allow list. Headings, paragraphs,
lists, emphasis, links, blockquotes, code and tables survive. `<script>`,
`<style>`, `<iframe>` and any `javascript:` URL do not.

The renderer also discards characters that change what text says without being
visible in it: the Unicode direction overrides, which reorder the characters
after them, and the zero-width characters, which let two words read as one.
Neither is reachable through the tag and attribute allow list, because neither
is a tag or an attribute, and what is rendered is stored permanently.

A host project that wants a different allow list subclasses `MarkdownRenderer`
and points the `MVP_COMPLIANCE_RENDERER` setting at it as a dotted path:

```python
# settings.py
MVP_COMPLIANCE_RENDERER = "myproject.rendering.MyRenderer"
```

`mvp_compliance.rendering.get_renderer()` resolves that setting, defaulting to
`MarkdownRenderer` when it is unset.

### Immutability

Once a version is published — current or superseded, `version.is_published` — its
`document`, `number`, `markdown`, `html` and `published_at` can never change again.
Only `status` can, because moving from current to superseded is the one change a
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

The guard on the four write routes above lives on `Version`'s default manager,
`VersionManager`, and the queryset behind it, `VersionQuerySet` — both importable
from `mvp_compliance.models`, and both plain subclasses with no configuration of
their own. `VersionManager.use_in_migrations` is set, so a historical `Version`
model inside a migration inherits the same guard.

Deleting a `Document` that still holds any version — draft, current or superseded —
raises `django.db.models.ProtectedError` and leaves the document in place; a
document holding none deletes normally. This is `Version.document`'s
`on_delete=PROTECT`, enforced by Django's deletion collector on every route,
including a queryset delete and a cascade from elsewhere — the package adds no
override on either side.

`mvp_compliance.exceptions.PublishedVersionError` is what every route above raises.

### Retrieval

The version in force — `document.current` — is a property returning the current
`Version`, or `None` when nothing has ever been published. `None` is a normal
answer, not an error:

```python
document.current  # the Version in force, or None
```

One version by its number, the plain Django idiom, no wrapper method:

```python
document.versions.get(number=2)
```

The published history, in order, with drafts absent — `VersionQuerySet.published()`,
reachable through the related manager on any document:

```python
document.versions.published()  # every version that has ever been current, in order
```

`VersionQuerySet` also carries `.drafts()`, the complement — every version that has
never been published — and `.current()`, the queryset `document.current` is built on
top of. All three are available both as `Version.objects.<method>()` and as
`document.versions.<method>()`.

## `Acceptance`

The record that one person accepted one published version, at one moment. It names
the user, the version and when it happened, and points at a version — never at a
document, because a document has said different things at different times and a
record naming only the document couldn't say which of them the person saw.

```python
from mvp_compliance.models import Acceptance

acceptance = Acceptance.objects.record(user, privacy.current)
acceptance.user        # the user
acceptance.version     # the exact Version they accepted
acceptance.accepted_at # the moment it happened
```

`Acceptance.objects.record(user, version)` is the only route that writes one.
Recording against a version that has never been published — `version.is_published`
is `False` — is refused:

```python
Acceptance.objects.record(user, draft_version)  # raises RecordError; writes nothing
```

A superseded version is accepted; only a draft is refused, because a draft has no
standing for anybody to agree to. There is no way to record an acceptance of a
`Document` — `Acceptance` has no field and no manager method that takes one.

Accepting a later version of the same document is a second record, not a change to
the first: the earlier acceptance is left exactly as it was, and both stand.

```python
version_one = Version.objects.create(document=privacy, markdown="# Privacy policy\n\n...")
version_one.publish()
first = Acceptance.objects.record(user, version_one)

version_two = Version.objects.create(document=privacy, markdown="# Privacy policy\n\n...v2")
version_two.publish()  # supersedes version_one
second = Acceptance.objects.record(user, version_two)

first.version  # still version_one — unchanged
Acceptance.objects.filter(subject=Acceptance.subject_of(user)).count()  # 2
```

Recording the same person's acceptance of the same version again — including two
attempts at once — succeeds and returns the record that already exists. It does not
raise and it does not write a second row:

```python
again = Acceptance.objects.record(user, version_two)
again == second  # True — the record that already existed, not a new one
Acceptance.objects.filter(version=version_two).count()  # still 1
```

A person's acceptances always come back in the order they happened, oldest first.

### Immutability

Once written, an acceptance is finished. Every route the package offers to change
or delete one is refused:

```python
acceptance.subject = "tampered"
acceptance.save()  # raises RecordedAcceptanceError; the stored row is untouched

Acceptance.objects.filter(pk=acceptance.pk).update(subject="tampered")  # same
Acceptance.objects.bulk_update([acceptance], ["subject"])  # same
acceptance.delete()  # raises RecordedAcceptanceError; an acceptance can't be deleted
Acceptance.objects.filter(pk=acceptance.pk).delete()  # same
```

The guard lives on `Acceptance`'s default manager, `AcceptanceManager`, and the
queryset behind it, `AcceptanceQuerySet` — both importable from
`mvp_compliance.models`. `AcceptanceManager.use_in_migrations` is set, so a
historical `Acceptance` model inside a migration inherits the same guard, and no
migration this package ships writes to one.

When a version an acceptance names is later superseded, the acceptance is
unaffected — it keeps pointing at the exact version the person saw.

`mvp_compliance.exceptions.RecordedAcceptanceError` is what every route above
raises; `mvp_compliance.exceptions.RecordError` is what recording itself raises
when it is refused.

### Outstanding

Whether a person has accepted what is currently in force is a plain question,
asked two ways:

```python
document.is_outstanding_for(user)        # one document
Document.objects.outstanding_for(user)   # every document, as a queryset
```

`is_outstanding_for` is `True` when `user` has not accepted the version currently
in force for that document — whether they never accepted anything for it, or
accepted a version that has since been superseded. `outstanding_for` names every
document in that state, in one query regardless of how many documents exist.

A document with no published version is never outstanding for anybody, because
there is nothing in force to accept.

This answer is deliberately unfiltered by whether a site chooses to enforce a
document — that decision belongs elsewhere, and this method does not carry it.
