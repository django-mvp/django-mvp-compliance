# Data model

The foundation everything else in this package sits on: a document with a lasting
identity, and the sequence of versions underneath it.

## `Document`

A named legal text — a privacy policy, a set of terms, a cookie policy. It has a
lasting identity, a unique `name` and a unique `slug`, and it holds no wording of its
own: every word lives in one of its versions.

```python
from mvp_compliance.models import Document

privacy = Document.objects.create(name="Privacy policy", slug="privacy-policy")
```

The `slug` is the document's identifier in its address: the page that shows the version
in force is served at `<prefix>/privacy-policy/`. See [pages.md](pages.md).

### Documents with a version in force

`Document.objects.in_force()` returns every document that has a current version, and
leaves out one that has only drafts and one that has no versions at all. Each document
comes back with its current version already fetched, as a list of one on
`current_versions`, so reading it costs no query per document:

```python
for document in Document.objects.in_force():
    version = document.current_versions[0]
    print(document.name, version.number)
```

## `Version`

One revision of a document, holding the Markdown its author wrote.

```python
from mvp_compliance.models import Version

Version.objects.create(document=privacy, markdown="# Privacy policy\n\n...")
```

A version belongs to exactly one document, through `Version.document`, and a
document's versions come back through `document.versions.all()` in the order they
were published, drafts last. `Version.number` is assigned when the version is
published: the year of publication, in the site's time zone, and its place among
the document's versions published that year, so `"2026.1"`, `"2026.2"`, then
`"2027.1"`. It is never supplied by whoever writes the version. A draft's number is
`None`, so drafts that are never published leave no gaps, and the database refuses
a second version with a number its document already has.

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

`publish()` takes the account doing it, `publish(publisher=user)`, and records it on the version
along with that account's primary key as text, written by the same
`Acceptance.subject_of()` an acceptance uses. Called without one, it records nobody:

```python
version.publish(publisher=request.user)
version.publisher  # the user
version.publisher_subject  # str(user.pk)
```

A draft has neither. `version.publisher_display` says what to show a person, and never
a removed account's identifier:

| The version | `publisher_display` |
|---|---|
| is a draft | `None` |
| was published by an account that still exists | `str(version.publisher)` |
| was published by an account since removed | "Account removed" |
| was published with nobody named, or before publishers were recorded | "Unknown publisher" |

Removing the publisher's account succeeds and leaves the version otherwise unchanged:
`publisher` becomes empty and `publisher_subject` stays.

Once the publication commits, `publish()` sends the `version_published` signal; see
[announcing.md](announcing.md).

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
`document`, `number`, `markdown`, `html`, `published_at`, `publisher` and `publisher_subject`
can never change again. The one exception is removing the publisher's account, which clears
`publisher` and keeps `publisher_subject`.
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
document.versions.get(number="2026.2")
```

The published history, in order, with drafts absent — `VersionQuerySet.published()`,
reachable through the related manager on any document:

```python
document.versions.published()  # every version that has ever been current, in order
```

`VersionQuerySet.with_replaced_at()` annotates each version with `replaced_at`, the
moment the next published version of the same document took over, and `None` for the
version in force. Drafts never count as a replacement. It costs no extra query however
many versions are read:

```python
for version in document.versions.published().with_replaced_at():
    print(version.number, version.published_at, version.replaced_at)
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

### Account removal

Closing an account is an administrative act, not a statement about the evidence, so by
default an acceptance survives the removal of the account it names:

```python
# settings.py
MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL = True  # the default
```

Under the default, deleting a user leaves their acceptances in place — `user` is
cleared to `None`, and `subject` still says whose the record is. **The cost of that
default is real and worth stating plainly: closing an account does not remove what
this package holds about that person.** A project bound by a stricter erasure
requirement sets the setting to `False`, and removing an account then takes that
person's acceptances with it. Either way, removing one account never affects anyone
else's records.

Because the `user` foreign key is cleared on the surviving path, a person's records are
found afterwards by the identifier that outlives it, not by their (now gone) account:

```python
Acceptance.objects.for_person(user)      # while the account still exists
Acceptance.objects.for_subject(subject)  # the same records, by the stored identifier —
                                          # what still works once the account is gone
```

Both come back in the order the acceptances happened. `for_person(user)` is a thin call
through `Acceptance.subject_of(user)` into `for_subject()`, so the two never disagree
about which records belong to whom.

A new account created with a username an old, removed account once had inherits
nothing: `subject` is derived from the account's primary key, never its username, so
the two accounts are never mistaken for one another.

#### Keeping surviving records findable

`subject` is the account's primary key and nothing else. Once the account row is gone,
nothing in the database maps that number back to a person. A dispute or a request
arrives as a name or an email address in a letter, and neither of them will find the
record.

**A project that keeps acceptances past account removal is responsible for keeping its
own record of whose identifier that was**, in its own table, written when the account is
closed:

```python
# myproject/compliance.py
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver


class ClosedAccount(models.Model):
    """What this project keeps so a surviving acceptance can still be found."""

    email = models.EmailField(verbose_name="email", help_text="The address this account used.")
    subject = models.CharField(
        max_length=255,
        verbose_name="subject",
        help_text="The identifier this person's acceptances carry.",
    )
    closed_at = models.DateTimeField(auto_now_add=True, verbose_name="closed at")


@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def remember_closed_account(sender, instance, **kwargs):
    ClosedAccount.objects.create(email=instance.email, subject=str(instance.pk))
```

Then a lookup starts from whatever the letter contains and ends at this package:

```python
subject = ClosedAccount.objects.get(email="someone@example.com").subject
Acceptance.objects.for_subject(subject)
```

This package holds no part of that map, under any setting. What a project may keep about
somebody who asked to be removed, and for how long, follows from its own lawful basis and
its own retention policy — neither of which a reusable package knows. Keeping the map in
the project's own table puts that data where those decisions already apply, and keeps this
package able to say truthfully that it retains nothing identifying about a removed account.

Without a map of some kind, surviving records are unreachable in practice. They exist, they
are complete, and nothing can match them to the person asking about them. That is not a
state worth holding personal data in: a project unwilling to keep the map is better off
setting `MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL` to `False` and letting
acceptances go with the account.

The reasoning, and the configurable alternative that was rejected, are in
[ADR 0014](adr/0014-the-project-links-a-surviving-acceptance-to-a-person.md).

### Optional evidence

An acceptance holds three facts by default: who accepted, which version, and when.
Nothing else — it is personal data about somebody who did not ask for it to be kept,
so the package holds none of it unless a project says so:

```python
# settings.py
MVP_COMPLIANCE_RECORD_IP_ADDRESS = False  # the default
```

Turned on, `record()` also holds the address the request came from, provided a request
is passed to it:

```python
Acceptance.objects.record(user, version, request=request)
```

Only `request.META["REMOTE_ADDR"]` is ever read, and never a forwarded header such as
`X-Forwarded-For`. That header is set by the client, so a package that trusted it would
have an evidence field the person the evidence concerns could fill in themselves — worse
than holding nothing. A project running behind a proxy or a load balancer is responsible
for making `REMOTE_ADDR` correct, which is ordinary Django deployment advice and is
solved by middleware the project chooses, not by this package guessing which of several
headers to trust.

`record()` called with no `request` — from a management command, a shell session, or a
caller that has no request to hand it — leaves `ip_address` empty even with the setting
on, so nothing has to be invented to satisfy it.

Turning the setting on or off never changes an existing record: `ip_address` is filled
in only at the moment `record()` creates a new row, and an acceptance is never edited
afterwards. A record made before the setting was turned on still holds nothing for that
field, and a record made while it was on still holds what it held once the setting is
turned off again.

### Producing what is held

Everything the package holds about one person, assembled into one answer rather than a
query per document:

```python
from mvp_compliance.records import produce

record = produce(subject)
```

`subject` is the same identifier `Acceptance.objects.for_subject()` takes — an account's
primary key while it still exists, or the identifier a record still carries once it is
gone.

`produce()` returns a frozen `PersonalRecord`. Its `sections` is a tuple of `Section`
objects, one per kind of record the package holds about that person — there is one
today, the acceptances — and each section's `entries` is a tuple of `AcceptanceEntry`
objects, each naming the document, the version accepted and the moment it happened:

```python
entry = record.sections[0].entries[0]
entry.document       # "Privacy policy" — the document's current name
entry.version         # "2026.1" — Version.number
entry.accepted_at     # the moment this acceptance was recorded
entry.ip_address      # the address the request came from, or None
entry.wording         # the HTML stored on that version at publication, in full
```

Each entry's `wording` is `Version.html` exactly as it was stored at publication — never
rendered again here, and never the current wording of a document whose version has since
been superseded. `produce()` reads the field; it never calls the renderer, so a later
change to `MVP_COMPLIANCE_RENDERER` or its allow list cannot alter what an entry shows for
an acceptance already recorded. A person with acceptances of several versions of one
document gets each entry carrying that version's own wording, never another's.

Every acceptance held for that person appears, including several acceptances of the same
document over time, and nothing belonging to anybody else. A person the package holds
nothing about still gets a normal answer rather than an error or an empty screen:

```python
produce("nobody-the-package-has-ever-heard-of").is_empty  # True
```

Producing an answer only reads — it writes nothing, and it reads no clock, so producing
the same answer twice with no change to the records gives an equal answer back.
