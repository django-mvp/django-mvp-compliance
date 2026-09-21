# Decisions — 001 Legal documents kept as versioned records

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — No retirement of a document

**Ambiguous**: a site drops a document it no longer offers, for instance a user agreement that has
been folded into the terms. Nothing in the roadmap says what happens to it.

**Chosen**: documents are not retired in this feature, and a document with published versions
cannot be deleted at all.

**Why defensible**: no roadmap item from R1 to R11 asks for it, so building it now is speculative.
The absence is also safe in the direction that matters: the failure mode of having no retirement is
a longer list of documents, while the failure mode of having retirement is a route that could take
published wording out of reach of somebody entitled to read it. If retirement arrives later it adds
a state to the document rather than changing anything specified here.

One consequence worth naming: `CONTEXT.md` has no word for a document that is no longer offered,
and both *archived* and *retired* sit on the avoid list under **Superseded**. Whoever specifies
retirement picks the word then.

## D2 — The package assigns version order, and there is no author-supplied label

**Ambiguous**: whether an author names a version ("v2.1", "January 2026 revision") and whether that
name has anything to do with ordering.

**Chosen**: order belongs to the package. No author-supplied label exists in this feature.

**Why defensible**: `django-termsandconditions` carries a `version_number` field that authors fill
in while the version actually in force is computed from a separate date field, so the number orders
nothing and can disagree with reality. Two sources of truth for ordering is the specific defect
worth avoiding. A human-readable label was raised and left out because it has no consumer yet.
Support staff and complaint responses need one, so it is likely to arrive with R10, where the
people needing it appear.

## D3 — Publication takes effect immediately

**Ambiguous**: whether a version can be prepared now and dated to take effect later, which is how
`django-termsandconditions` works and a recognisable need for a policy with a notice period.

**Chosen**: publishing takes effect the moment it happens.

**Why defensible**: a scheduled publish means the version in force is computed from a clock rather
than stored, which makes "which version was in force at the instant this person agreed" a
calculation rather than a fact. That calculation is exactly what the evidence property cannot
afford. It also weakens publishing as a deliberate act, which issue #5 depends on. A site needing a
notice period can publish on the day, and a later feature can add scheduling as a queued act that
still resolves to a stored state.

## D4 — No rollback to an earlier published version

**Ambiguous**: whether a bad publish can be undone by making the previous version current again.

**Chosen**: no. Restoring earlier wording means publishing that wording again as a new version.

**Why defensible**: a rollback makes publishing two-way and breaks the one-way rule the package
exists to provide. It also destroys the history: a document whose current version moves backwards
has no honest answer to "what was in force in March". Republishing the old wording costs one
version and leaves a truthful record of what happened.

## D5 — No screens, no addresses

**Ambiguous**: whether a model-layer feature registers anything in the admin, given that without a
surface nobody can exercise it by hand.

**Chosen**: nothing. No admin, no forms, no views, no URLs.

**Why defensible**: the authoring surface is issue #5 and the reading surface is R2, both of which
follow immediately. An admin registration here would be written to be replaced, and the throwaway
version is the one that tends to survive. Tests exercise the rules, and they are the right consumer
for a feature whose entire value is a set of invariants.

## D6 — Deleting a document that has published versions is refused

**Ambiguous**: the constitution forbids editing a published version but says nothing about deleting
the document above it, which would take the versions with it.

**Chosen**: the package offers no way to delete a published version, and no way to delete a
document holding any.

**Why defensible**: an immutability rule with a cascade underneath it is not an immutability rule.
This closes the loophole rather than adding a policy, and it follows from Article XII rather than
extending it. A document created by mistake and never published can still be deleted, because
nothing has been put in front of anybody.

## D7 — Empty rendered output is refused at publication

**Ambiguous**: what happens when authored markup produces nothing, for instance a version whose
entire body is a comment.

**Chosen**: publication is refused.

**Why defensible**: an empty document in force is indistinguishable from a bug, and the alternative
is a site with a privacy policy page showing nothing while acceptance records accumulate against
it. Refusing at publication is the cheap moment to catch it, and it cannot be caught later because
a published version cannot be corrected.
