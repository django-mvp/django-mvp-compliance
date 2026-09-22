# Django MVP Compliance

Privacy policies, terms, user agreements and cookie notices for
[django-mvp](https://github.com/django-mvp/django-mvp) projects — written and
published from the database, with a record of who accepted which version and
when.

This package is not usable on its own. It renders on the django-mvp app shell
(DaisyUI 5 + Tailwind CSS v4 + django-cotton) and expects it.

> **Status: early development.** `Document` and `Version` — versioned legal
> text, authored in Markdown and published with an immutable record — are
> built, and both are registered in the Django admin for writing them. No
> preview, no publish confirmation, no consent recording and no account-area
> page exist yet.

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

privacy = Document.objects.create(name="Privacy policy")
version = privacy.versions.create(markdown="# Privacy policy\n\n...")
version.publish()
```

Publishing renders the Markdown to HTML once and makes that version
**current** — the one in force — moving whichever version was current
before it to **superseded**. A published version's wording can never change
again; a correction, of any size, is published again as a new version.
There is no way to unpublish, revert, or make an earlier version current a
second time.

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
  page and the hooks. Gathering, exporting and erasing a person's data across
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

The standing directions this package steers by are in [GOALS.md](GOALS.md).

## Prior art

`django-termsandconditions` and `django-tos` both store terms in the database
and track acceptance, and `django-cookie-consent` handles cookie categories and
script gating well. If you want any of those problems solved on their own, use
them. The reasoning behind building anyway, and what does and does not overlap,
is in [docs/brainstorm.md](docs/brainstorm.md).

## Licence

MIT.
