# ADR 0031 — A version can be locked for translation before it is published

**Status:** accepted

## Decision

A version has four states: draft, pending, current and superseded. `Version.lock_for_translation()`
takes a draft to pending, and `Version.return_to_draft()` takes it back. Both require the
`publish_version` permission in the admin. A pending version's `document`, `markdown` and `summary`
are frozen by the same guards that freeze a published version, including on the historical model in
a migration. In every other respect it is a draft: it has no number, no publication time, no stored
HTML and no publisher, nobody can accept it, readers never see it, and it can be deleted.

`Version.objects.published()` and `Version.is_published` mean current or superseded only. A
translation can be written only for a pending or published version. Returning a pending version to
draft returns every translation of it that was put live to draft, with its wording kept.

## Why

A translation has to be written against wording that will not change, or it can go live describing
text that was never published. Translating only after publication would leave every new version in
force untranslated for a while. A frozen state before publication lets a version and its
translations launch together, and keeps publication itself the one act that gives a version
standing.

Locking fixes the wording, which is the decision publishing makes, so it takes the same permission.

## Revisit if

A site needs to translate wording that is still being drafted, or a pending version needs standing
of its own, such as being shown to readers before it is in force.
