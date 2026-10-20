# Decisions — 011 Declaring the documents a site links to

Rationale too long to sit inside `spec.md`, and the record of each ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen and why the choice is
defensible.

## The reading this specification is written to

A developer lists the documents the site links to in the project's settings, by slug and name.
Migrating creates any that are missing, with no version, so every environment has them and whoever
manages the documents finds them in the admin. A declared document's slug is fixed from the start.
Its name is a starting value, and its kind and enforcement are never declared. Undeclared documents
are unchanged.

## D1 — Declared in the settings, not as classes

**Ambiguous**: the idea that started this feature was a declarative class per document, carrying
methods that look the document up and give its address without raising when it does not exist.

**Chosen**: a setting naming each document's slug and name. Templates keep linking through the
address the pages already document.

**Why defensible**: a class would hold nothing a settings entry does not, and would need a base
class, a registry and discovery of the modules that hold the classes. A template would still have
to reach it by a string key. Article III rules out a wrapper layer with no second use. The address
already never raises: it is built from the slug without reading the database, and it always shows
the version in force. django-dynamic-preferences shows where per-item classes lead: an
autodiscovered module and a management command to reconcile the rows with the classes.

**ADR:** docs/adr/0026-a-project-declares-the-documents-it-links-to-in-a-setting.md

## D2 — Created when the database is migrated

**Ambiguous**: whether a declaration creates anything in the database at all, and if so when.

**Chosen**: migrating creates each missing declared document with no version, and never updates or
deletes one.

**Why defensible**: without a document in the database the declaration binds only the developer.
Whoever manages the documents could still create it under another slug, and nothing would notice.
The document carries no wording and no version, so it publishes nothing and claims nothing.
Django's own pattern for state that code declares is to create the missing rows after migrating
and leave existing ones alone: permissions from `Meta.permissions`, and the default site.

Other packages create the row the first time something reads it: django-constance,
django-dynamic-preferences, Wagtail's settings, django-solo, django CMS's static placeholders and
django-legaltext. That was rejected because drawing a page would write to the database, and which
documents an editor sees would depend on which pages had been visited.

**ADR:** docs/adr/0026-a-project-declares-the-documents-it-links-to-in-a-setting.md

## D3 — No template tag

**Ambiguous**: whether templates need a new way to reach a declared document.

**Chosen**: none. A template links with the address the pages already document.

**Why defensible**: the address works in every environment the moment the document is declared,
and leads to the version in force once one is published. A tag that hides a link until a version is
in force is a separate want, and nobody has asked for it yet.

**ADR:** docs/adr/0026-a-project-declares-the-documents-it-links-to-in-a-setting.md

## D4 — A conflicting declaration stops the run

**Ambiguous**: what to do when a declared name belongs to another document, or a declared slug is
one no document may have.

**Chosen**: migrating reports the declaration and what it conflicts with, and creates no declared
document in that run.

**Why defensible**: names are unique, so the document cannot be created as declared. Skipping it
quietly would leave the code linking to a document that will never exist. Creating the others and
skipping one would leave a database that half matches its settings.

**ADR:** none — the refusal on a conflict is stated in ADR 0026's decision; the rest is local to this feature.

## Design review

One reviewer, three lenses, verdict approve, no critical or high finding. Remedies applied to the
plan and tasks:

- The admin appends `slug` to the read-only fields once, under one condition, not twice (ARCH-001).
- US-1 is built before US-2 (SPEC-001).
- The receiver reads and writes through `using` (ARCH-002).
- `bulk_create(update_conflicts=True)` is documented as unguarded, as for the published lock
  (SEC-001).
- T001 tests that publishing a declared document fills its address (SPEC-002).
- A name with surrounding whitespace is refused (ARCH-003).

ADR 0019's Decision is edited to read as the current rule in US-2.

**ADR:** none — the remedies are local to this feature's plan.

## D5 — A declared slug refuses with its own exception

**ADR:** none — follows ADR 0003, which already has every refusal raise a package exception.
