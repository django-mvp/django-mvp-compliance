# Django MVP Compliance

Privacy policies, terms, user agreements and cookie notices for
[django-mvp](https://github.com/django-mvp/django-mvp) projects — written and
published from the database, with a record of who accepted which version and
when.

This package is not usable on its own. It renders on the django-mvp app shell
(DaisyUI 5 + Tailwind CSS v4 + django-cotton) and expects it.

> **Status: 0.0.1, scaffold only.** The repository is set up and green. No
> models, pages or components have been built yet.

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

## Scope & philosophy

**What it is**

- A store for versioned legal documents, authored in Markdown and rendered as
  pages in your site's shell.
- A record of consent: which user accepted which version of which document, and
  at what time.
- Enforcement, so a user who has not accepted the current version is asked to
  before continuing.
- Cookie consent, gathered and recorded alongside everything else.
- A place in the account area where a signed-in person can see what they have
  agreed to and what they have chosen.

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

**Tie-breaks**

1. A published version is immutable. Everything else gives way to that, because
   an editable record of what someone agreed to is not a record.
2. Prefer what the host project already runs. Rendering, styling and navigation
   come from django-mvp rather than from anything shipped here.
3. Record over enforce. When the two conflict, keeping an accurate account of
   what happened wins.

## Prior art

`django-termsandconditions` and `django-tos` both store terms in the database
and track acceptance, and `django-cookie-consent` handles cookie categories and
script gating well. If you want any of those problems solved on their own, use
them. The reasoning behind building anyway, and what does and does not overlap,
is in [docs/brainstorm.md](docs/brainstorm.md).

## Licence

MIT.
