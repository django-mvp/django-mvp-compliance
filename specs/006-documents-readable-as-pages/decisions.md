# Decisions — 006 Documents and their versions readable as pages of the site

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — A document's address comes from a slug, not its name

**Ambiguous**: the issue asks for an address that keeps working, and a document today has only a
name. The name is the obvious thing to build an address from.

**Chosen**: each document gains a slug, suggested from its name, editable until the document's first
version is published and fixed from then on (FR-015 to FR-017). The name stays editable for ever.

**Why defensible**: names get reworded. "Terms" becomes "Terms of use", and a privacy policy gets
renamed when a site adds a second one for a different audience. An address built from the name
would break every footer link and every link already sent to somebody at exactly that moment, which
is the failure the issue exists to prevent. Freezing at first publication rather than at creation
lets a typo be fixed while it costs nothing, because no address is served until something is
published. This follows the same rule as the rest of the package: what has been published is not
changed.

## D2 — The existing document tests gain a slug

**Ambiguous**: adding a unique, required slug means every test that creates a document inline
without one now fails on the second document, because an unset slug is the empty string and two
empty strings collide. Changing a test this feature did not write is normally refused.

**Chosen**: the inline creations in `tests/test_models.py::TestDocument` each get a distinct slug,
with no assertion changed. `test_duplicate_name_is_refused` gives its second document a different
slug, so that it keeps proving the name constraint rather than passing on the slug one.

**Why defensible**: the tests are rewritten only to supply a value the model now requires. What
they assert is unchanged, and the one test whose meaning a shared slug would have silently changed
is adjusted so that it still tests what its name says. Found by the design review (SPEC-001).

**ADR:** none — a local test adjustment, nothing downstream inherits it.

## D3 — Design review outcome

One verified high finding (SPEC-001, D2 above) and three low ones. All four were applied as edits
to `tasks.md` and `plan.md`: T001/T002 fix the existing tests and the demo seed in the same task
that adds the slug, T002 adds the manager forwarder, the views section says what each view must
override, and T024 gains the no-compliance-claim assertion. The note that `pyproject.toml` lists
only Django 5.2 and 6.0 was checked and is wrong: 6.1 is listed.

**ADR:** none — a record of this feature's review, not a durable decision.
