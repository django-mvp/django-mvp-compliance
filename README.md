# Django MVP Compliance

Privacy policies, terms, user agreements and cookie notices for
[django-mvp](https://github.com/django-mvp/django-mvp) projects — written and
published from the database, with a record of who accepted which version and
when.

This package is not usable on its own. It renders on the django-mvp app shell
(DaisyUI 5 + Tailwind CSS v4 + django-cotton) and expects it.

> **Status: early development.** `Document` and `Version` — versioned legal
> text, authored in Markdown and published with an immutable record — are
> built, and both are registered in the Django admin for writing,
> previewing and publishing them, behind a confirmation step and a
> permission of its own. So is `Acceptance` — recording who accepted which
> version, and when. `mvp_compliance.records.produce(subject)` assembles
> everything the package holds about one person into a single answer, and
> the admin's **Everything held about a person** page is what calls it,
> behind a permission of its own that nobody holds by default. No
> account-area page exists yet.

## Why

A legal document has a lifecycle that source control serves badly. It gets
reworded on advice, it acquires a new clause, and the day it changes you need
two things at once: the new text in front of users, and proof of what the old
text said to everyone who agreed to it. Keeping policies in templates means a
deployment for every wording change and a `git log` as the only evidence trail.

So the documents live in the database. They are written in Markdown, published
as ordinary pages on your site, and a published version never changes again —
a correction is a new version, and the acceptance record points at the exact
version a person saw.

## Models

`Document` is a named legal text — a privacy policy, a set of terms, a
cookie policy — with a lasting identity and no wording of its own. `Version`
holds the Markdown wording and belongs to one document. A new version is a
**draft**: no legal standing, invisible to readers, freely editable and
freely discardable.

```python
from mvp_compliance.models import Document

privacy = Document.objects.create(name="Privacy policy", slug="privacy-policy")
version = privacy.versions.create(markdown="# Privacy policy\n\n...")
version.publish()
```

Publishing renders the Markdown to HTML once and makes that version
**current** — the one in force — moving whichever version was current
before it to **superseded**. A published version's wording can never change
again; a correction, of any size, is published again as a new version.
There is no way to unpublish, revert, or make an earlier version current a
second time.

A version is numbered when it is published, never before: the year it was
published and its place among that document's versions published in the same
year, so `2026.1`, `2026.2`, then `2027.1`. A draft has no number, so drafts
that are never published leave no gaps in the published history.

The version in force:

```python
privacy.current  # the current Version, or None if nothing has been published
```

The published history, in order, drafts absent:

```python
privacy.versions.published()
```

Rendering is `mvp_compliance.rendering.MarkdownRenderer`, configured by one
setting:

```python
# settings.py
MVP_COMPLIANCE_RENDERER = "myproject.rendering.MyRenderer"  # optional
```

`MVP_COMPLIANCE_RENDERER` is a dotted path to the renderer class, and
defaults to `MarkdownRenderer` when unset. A host project that wants a
different HTML allow list points it at a subclass.

`Acceptance` is the record that one user agreed to one published version, at
one moment. It names the user, the version and when it happened, and once
written it is finished — nothing in this package will edit it or delete it.

```python
from mvp_compliance.models import Acceptance

Acceptance.objects.record(user, privacy.current)
Document.objects.outstanding_for(user)
```

Recording against a version that has never been published is refused; there
is no way to record an acceptance of a `Document`, only of one of its
versions. `outstanding_for()` answers which documents have a version in force
that this user has not accepted.

By default an acceptance survives the removal of the account it names — closing an
account does not remove what this package holds about that person:

```python
# settings.py
MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL = True  # the default
```

Set it to `False` and removing an account takes that person's acceptances with it.
`Acceptance.objects.for_subject(subject)` finds a person's records by the identifier
that survives their account being removed, once `user` itself is no longer there to
find them by.

That identifier is the removed account's primary key, and this package holds nothing
else that identifies anybody once the account is gone. Keeping the default therefore
comes with an obligation: the project has to keep its own record of whose identifier
that was, written when the account is closed, or the surviving acceptances are complete
and unreachable. See
[Keeping surviving records findable](docs/models.md#keeping-surviving-records-findable).

By default an acceptance holds nothing about a person beyond who they are, which
version, and when. A site that wants the address a request came from too, because it
makes a record harder to dispute, turns that on and passes the request along:

```python
# settings.py
MVP_COMPLIANCE_RECORD_IP_ADDRESS = False  # the default

# a view
Acceptance.objects.record(user, privacy.current, request=request)
```

Off by default, because it is personal data about somebody who did not ask for it to
be kept. On, and recorded from a call that supplies no request, the field stays empty
rather than inventing a value. Turning the setting on or off only ever affects
acceptances recorded afterwards — an existing record keeps whatever it held when it
was written. See [docs/models.md](docs/models.md) for the full surface.

## Writing a version

`Document` and `Version` are registered in the Django admin, and writing a
version is what that admin surface is for. Its `markdown` field carries a
formatting toolbar over an ordinary textarea — headings, bold, italics,
bulleted and numbered lists, links and block quotes — for a compliance
editor who is not assumed to know Markdown. There is no image, embed,
table, tagging or raw HTML control: a legal document is structured prose,
and every button offered is one somebody has to be supported in using.
Typing Markdown directly works too, because either way what is stored is
ordinary Markdown.

The controls agree with what publication keeps: nothing the toolbar can
produce is stripped when the version is published.

The toolbar is drawn by [EasyMDE](https://github.com/Ionaru/easy-markdown-editor),
vendored into the package rather than fetched, with its own icons in place
of the icon font it expects and does not ship.

## Previewing a version

A version's change page carries a Preview link, at `<version>/preview/` in
the admin. It shows the rendering the published page will actually use —
content the sanitiser's allow list would strip is shown stripped, so that
loss is visible before publication rather than discovered after.

This is a different thing from the toolbar's own inline formatting display
while writing: the toolbar approximates, and the preview is the real
output. For a draft, that output is rendered fresh from the current
wording. For a published version it is read from the HTML stored at
publication — never rendered again, because that stored HTML is the
evidence of what a reader was served.

Reaching a version's preview needs permission to view it — `view_version`
or `change_version`, the same test the admin applies to its change page.

## Permissions

Reaching a version in the admin at all needs Django's own `view_version` and
`change_version` permissions — the compliance editor of this package holds
both, alongside `add_version` and `delete_version` for writing and
discarding drafts. Nobody without them reaches a draft, a document, or a
version's changelist: the admin refuses the request before any page of
ours renders, so a draft stays invisible to a visitor, a signed-in account
that isn't staff, and staff holding none of these permissions.

Deleting a version needs `delete_version` too, and it is refused once that
version has been published, regardless of who is asking — discarding is
for drafts.

Publishing needs `publish_version`, held separately from the permissions
above. Writing a draft and making something legally binding are different
levels of trust, so a compliance editor holding every permission except
this one can prepare a version and cannot put it live, and — the unusual
but coherent alternative — somebody holding only `view_version` and
`publish_version` can approve wording somebody else wrote and write
nothing themselves. Without `publish_version` the publish address is
refused by both the page that confirms and the action that publishes it,
and no link to it is offered.

## Publishing

Publishing is the one act in this package there is no way back from, so it
is never a side effect of saving. A version's change page offers a
**Publish** link once it is a draft, to whoever holds `publish_version`.
Following it asks for confirmation first: the page names the document and
version, shows the rendering that is about to go live, and says plainly
that the wording cannot be changed afterwards and that a correction is
published as another version. Nothing is published until that page is
posted. Following its **Back** link instead leaves the draft untouched.

`publish()` refuses a version that is not a draft and one whose rendered
output is empty once stripped — both reach the person publishing as a
message they can read, not as an error page.

The admin records whoever published a version as its publisher, and shows
them next to the moment of publication. Code can call
`version.publish(publisher=user)` to do the same, or `version.publish()` to
record nobody. See [docs/models.md](docs/models.md) for what a version says
about a publisher whose account has since been removed.

Once a version is published, its change page in the admin offers no
editable form at all. Its wording is readable in full, and Django serves
its own read-only page rather than one this package builds — not a form
whose fields are disabled, and not one whose save is silently refused.

## Starting the next version from the one in force

A version that is currently in force offers a **Start the next version**
link on its own change page, next to Preview. It opens the version add
form with the document already chosen and that version's Markdown already
in the box — a correction usually changes one clause, not the whole text,
so starting from what is already there is the ordinary case.

A document's own change page offers **View current version**, leading to
that page, and **Version history**, leading to the versions list already
narrowed to this document. **View current version** is absent for a
document with nothing in force — no versions at all, or only a draft —
and **Version history** is offered either way.

A version can only be added from a document: neither control above hands
somebody a form with nothing chosen to write into, a bare request for the
add form is refused, and the versions list itself offers no way to add
one.

Saving a next version whose wording says exactly what the one in force
already says is refused, with a message saying so — a version that
changes nothing would supersede a wording with its own duplicate. A
document's first version is never refused this way: there is nothing
published yet to compare it against.

Nothing is copied on the server: the wording is read once and handed to a
new, unsaved form as a starting point. The version it came from is never
opened for writing, and the model would refuse it if anything tried.

## Scope & philosophy

**What it is**

- A store for versioned legal documents, authored in Markdown and rendered as
  pages in your site's shell.
- A record of consent: which user accepted which version of which document, and
  at what time.
- Enforcement, so a user who has not accepted the current version is asked to
  before continuing.
- Translations, so a reader sees a document in their own language.
- Cookie consent, gathered and recorded alongside everything else.
- A place in the account area where a signed-in person can see what they have
  agreed to and what they have chosen.

Each version has one canonical text, and that is the text an acceptance points
at. Translations exist so people can read a document in their own language, and
carry the usual notice that the canonical version governs. Adding a translation
later does not create a new version for everyone who already accepted.

**What it deliberately is not**

- **It does not make you compliant.** It provides the mechanics. Whether your
  policies say the right things, whether you have a lawful basis, and whether
  you honour what you promise are yours and your lawyers' to answer.
- **It does not fulfil data subject access requests.** It offers the account
  pages and the hooks. Gathering, exporting and deleting a person's data across
  your own models is the project's work, because only the project knows where
  that data is.
- **It is not a CMS.** The documents it manages are the legal ones. Nothing
  here is aimed at general page content.

**When it cannot be recorded, it did not happen**

This is the principle that settles the close calls. Someone who clicks "I
accept" and whose acceptance fails to save has not accepted: they see the page
again rather than continuing with nothing behind them. A check that cannot
reach the data telling it whether someone has accepted does not assume they
have.

Letting a person through and reconciling afterwards is the other available
answer, and it is the wrong one here. A gap in enforcement is a gap. A person
using the site with no record of what they agreed to is the thing this package
exists to prevent.

**The record is evidence, and evidence outlives convenience**

A published version never changes, and an acceptance is never edited or
deleted, because both are records of something that happened. A typo in a
published policy is corrected by publishing another version. A person who
asks for their data to be deleted still leaves their acceptances behind: they
are the evidence of what that person agreed to, and a dispute can arrive after
the account has gone.

The HTML a reader was served is stored at publication and served from then on.
Rendering the Markdown again later could produce something different after a
library upgrade or a change to the sanitiser, which would quietly change what
the record says a person was shown.

**It holds as little about a person as it can**

Everything stored about a person is personal data, so each field has to earn
its place, and anything optional is off until the project switches it on. An IP
address on an acceptance is the usual example: it strengthens the evidence, and
whether to keep it is the project's decision.

The standing directions this package steers by are in [GOALS.md](GOALS.md).

## Documentation

- [docs/models.md](docs/models.md) — documents, versions, publishing, and what a published
  version guarantees.
- [docs/pages.md](docs/pages.md) — serving a document as a page of your site: mounting the
  addresses, linking to a document, and what a visitor sees.
- [docs/announcing.md](docs/announcing.md) — the signal sent when a version is published, what it
  carries, and what happens when a receiver fails.
- [docs/authoring.md](docs/authoring.md) — the admin surface: the editor and what it offers,
  the form, and reading a version back the way the public will see it.
- [docs/disclosure.md](docs/disclosure.md) — producing everything held about a person: the
  page, its permission, and what the answer contains.
- [docs/adr](docs/adr) — the decisions behind the design, and why the alternatives were not
  taken.

## Prior art

`django-termsandconditions` and `django-tos` both store terms in the database
and track acceptance, and `django-cookie-consent` handles cookie categories and
script gating well. If you want any of those problems solved on their own, use
them. The reasoning behind building anyway, and what does and does not overlap,
is in [docs/brainstorm.md](docs/brainstorm.md).

## Licence

MIT.
