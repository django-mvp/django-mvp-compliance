# Decisions — 007 Documents that are read but never agreed to

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible. The five rulings made while specifying are in `spec.md` under *Clarifications*.

## D1 — The kind is a two-valued choice field, not a boolean

**Ambiguous**: "a document people agree to, or a notice" could be stored as `is_notice`, a boolean,
or as a `kind` field with two named values.

**Chosen**: `Document.kind`, a `CharField` with `Document.Kind.AGREED` ("agreed", *Agreed to*) and
`Document.Kind.NOTICE` ("notice", *Notice*), defaulting to `AGREED`.

**Why defensible**: the spec's own vocabulary is "its kind", and FR-009 asks the admin to show the
kind. A choice field shows it in words in the list column and the form without a display method,
and code that reads it (`kind == Document.Kind.NOTICE`) says what it means. The cost over a boolean
is nothing: one column either way.

**Revisit if**: a third kind is ever wanted. It would be a value, not a new field.

**ADR:** none — local to this model; the field and its values are documented in `docs/models.md`.

## D2 — `kind` is not indexed

**Ambiguous**: Article IX asks that a field with a plausible filter path be indexed, and
`outstanding_for()` filters on `kind`.

**Chosen**: no index.

**Why defensible**: the column has two values and the table holds tens of rows, one per legal text a
site publishes. The query that filters on it already reads the documents table in full for the
version join, and no planner would choose a two-valued index over that. An index would cost a write
on every document save for no read it could speed up.

**Revisit if**: a site's documents table grows to thousands of rows, which nothing in the spec or
the roadmap anticipates.

**ADR:** none — a sizing call about one column, recorded here as Article IX asks.
