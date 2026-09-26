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
