# Why translations are not built on a translation package

Django has two well-established packages for translating model fields:
[django-modeltranslation](https://pypi.org/project/django-modeltranslation/) and
[django-parler](https://pypi.org/project/django-parler/). This package uses neither. A
translation of a version is its own model, `Translation`, described in
[Data model](../models.md). This page explains why.

The short answer is that both packages solve a different problem. They make a field readable in
several languages and keep **one editable wording per language**. A translation of a legal
document has to keep **every wording it has ever had**, and none of them may change once it has
been put live.

## What a translation has to do here

Four requirements decide it. Each one follows from what the package exists to provide.

- **Every wording is kept.** A person may agree to a version while reading its German
  translation. Later, someone may need to see exactly what that person read. So a correction
  never replaces a wording. It adds a new one, and the earlier one stays on record with the dates
  it was live.
- **A wording is frozen once it is put live.** This is the same rule a published version follows.
  It has to hold on the model, on the queryset, and inside a migration.
- **The version's own text stays where it is.** The version's wording is what every acceptance
  points at and what governs. It never moves, and it is never rewritten.
- **A translation goes through drafts, a preview and putting live.** Its HTML is rendered once and
  stored, exactly as a version's is.

## django-modeltranslation

django-modeltranslation adds one column per language to the translated model's own table, so
`markdown_de`, `html_de` and so on would sit on `Version`'s own row.

- **Writing a translation would be an update to a published version.** The package refuses those
  outright. Exempting the new columns would leave the one table the package exists to protect
  partly writable.
- **One column per language holds one wording.** A correction would overwrite it.
- **The columns depend on each site's `LANGUAGES`.** The project has to generate migrations for
  the translated app whenever a language is added. For a reusable package, that means migrations
  generated inside an installed package, different on every site, and never shipped.

## django-parler

django-parler keeps translations in a separate table, one row per object and language. That
avoids modeltranslation's main problem, because translating a version would not write to the
version's own row. It still does not fit:

- **It keeps one row per language.** A correction overwrites the wording in place. The history
  of earlier wordings would have to be built next to it, and that history is most of what
  `Translation` is.
- **The main language would move into its table.** django-parler treats the site's default
  language as one more translation. The version's own wording would leave `Version` for
  django-parler's table, which breaks the version's immutability guards. It would also mean
  rewriting every stored version in a migration, which this package never does to a published
  version.
- **It has no drafts, no putting live, no stored rendering and no freezing.** Every one of those
  rules would sit on top of django-parler and work against its admin, which edits translations in
  place.
- **It does not declare support for every Django release this package supports.**

What django-parler would have given is language tabs in the admin and a fallback to another
language when an object is read. The fallback is a single query over `Translation.objects.live()`,
falling back to the version's own text.

## What was built instead

`Translation` is shaped like `Version`, and follows the same rules:

- Each row is one wording.
- A wording starts as a draft and is previewed through the same rendering.
- It is put live behind a permission of its own.
- Its HTML is stored when it is put live.
- From then on it is frozen, by a guard that holds in migrations too.

The decision is recorded in
[ADR 0032](../adr/0032-a-translation-keeps-every-wording-it-has-had.md).

## When to look again

If a translation ever had to be editable in place, or the package stopped needing to show what a
person read, this would be worth looking at again. A translation could then be a convenience for
readers rather than a record. django-parler would then be the package to start from.
