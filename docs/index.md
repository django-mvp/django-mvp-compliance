# django-mvp-compliance

Privacy policies, terms, user agreements and notices for
[django-mvp](https://github.com/django-mvp/django-mvp) projects, written and published from
the database, with a record of who accepted which version and when.

A legal document gets reworded on advice, and the day it changes you need two things at once:
the new text in front of people, and proof of what the old text said to everyone who agreed to
it. So the documents live in the database. They are written in Markdown, published as ordinary
pages on the site, and a published version never changes again. A correction is a new version,
and the record of an agreement points at the exact version a person saw.

## Where to look

- [How to use the demo](how-to/use-the-demo.md) is where to start in the demo project: who to
  sign in as, and what each account shows.
- [Writing and publishing a document](authoring.md) and [Data model](models.md) cover the
  documents themselves, in the admin and in code.
- [Pages](pages.md) and [Enforcement](enforcement.md) cover what a visitor and a signed-in
  person see, and how the site asks a person to agree.
- [Announcing a publication](announcing.md) and
  [Producing everything held about a person](disclosure.md) cover what the package tells your
  code, and what it can produce about one person.
- The how-to guides cover a person's own data: declaring what the project holds about them, and
  letting them delete their account.

```{toctree}
:hidden:

how-to/use-the-demo
```

```{toctree}
:caption: Documents
:hidden:

authoring
models
announcing
```

```{toctree}
:caption: Pages
:hidden:

pages
enforcement
```

```{toctree}
:caption: A person's data
:hidden:

disclosure
how-to/declare-what-the-project-holds-about-a-person
how-to/delete-an-account
```
