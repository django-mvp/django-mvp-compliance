# ADR 0032 — A translation keeps every wording it has had

**Status:** accepted

## Decision

`Translation` holds one row per wording of one version in one language. The rows for a version and
a language are that version's translation into the language. The current row is the wording
readers are served, and each superseded row is an earlier one, with the time it went live and the
time it was replaced. A correction is a new row put live, never an edit. A wording added for a
language that already has a translation is a correction of it.

A translation is live when its row has been put live and its version is published. Nothing stores
that: one put live on a pending version goes live when the version is published. A wording's
fields are frozen from the moment it is put live, whether or not its version is published yet, on
the instance, on the queryset and on the historical model in a migration, by a guard that names
`Translation` directly. Returning a pending version to draft is the one change it allows: its
translations return to draft with it.

The version's own wording is never touched by a translation, and it is still the text every
acceptance points at.

## Why

A person may agree to a version while reading a translation of it, and what they saw has to be
producible later, exactly as it was. A translation that could be overwritten would lose that while
leaving the version untouched. Keeping each wording as a row reuses the rules a version already
follows: drafts, a preview, publication behind its own permission, HTML stored once.

django-modeltranslation and django-parler were considered. Both keep one editable wording per
language, and django-modeltranslation stores it in columns on the version's own row, which the
version's immutability rules forbid.

A shared abstract base for the version and translation guards was considered and dropped: Django
leaves abstract bases out of the models it builds for migrations, so the guard would not hold
there.

## Revisit if

A site needs a translation to be agreed to as a text in its own right, so that it governs rather
than the version.
