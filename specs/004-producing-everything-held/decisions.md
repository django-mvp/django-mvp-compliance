# Decisions — 004 Producing everything held about one person's acceptances

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — One answer about a person, not a report about acceptances

**Ambiguous**: R3 asks for a person's *agreements* to be producible, which reads as a report about
acceptances. But R8 will hold cookie choices and R9 will show a person their own consent, and both
are answers about the same person. Either this feature is the package's one answer and those join
it, or it is the first of three.

**Chosen**: the package's one answer about a person, built now over acceptances because that is all
the package holds.

**Why defensible**: Sam's ruling, and it is the reading the constitution already implies. A site
fielding a request wants what is held about this person, not what is held about this person in each
of the package's subsystems. Three places to look is how a partial answer gets handed over by
accident, which Article XIV singles out as worse than no answer. The cost is one requirement's
worth of structure now (FR-017) against a surface that R8 would otherwise have to either duplicate
or retrofit onto, with real records already in it.

What this deliberately does not mean: no abstraction is built today for records that do not exist.
The requirement is that adding a kind of record does not change what the answer is, which is a
constraint on the design rather than a licence to build a plugin system for one caller.

## D2 — Producing an answer is a privileged act with a permission of its own

**Ambiguous**: R3 says nothing about who may produce the answer, and the obvious reading is that
anybody who can already reach the site's staff surfaces can.

**Chosen**: a permission of its own, held by nobody by default.

**Why defensible**: this is the one place in the package where one person's consent history is
assembled and handed over, which makes it the highest-value surface here by some distance. Reusing
whatever permission governs editing documents would give every compliance editor the ability to
pull any member of the public's record, which is a different job with different risk. Held by
nobody by default because a permission that arrives switched on is one nobody decided to grant.

Refusals reveal nothing about whether the named person has records (FR-013), because a refusal that
distinguishes the two turns the surface into a way of confirming that a given person uses the site.

## D3 — The wording travels with the answer, in full

**Ambiguous**: whether each entry carries the wording served or points at where it can be read.
Pointing keeps the answer small, which matters when somebody has a dozen acceptances of long
documents.

**Chosen**: in full.

**Why defensible**: the wording *is* the evidence, which is why FS-001 fixes it at publication and
Article XIII forbids producing it again later. A reference is a promise that something will still
be there and still say the same thing when somebody follows it, and the whole premise of this
package is that promises about text are worth less than the text. An answer handed to a regulator
that says "the wording is at this address" has answered nothing.

The size cost is real and accepted. An abridged answer is not evidence, so there is no version of
this that is both smaller and correct.

## D4 — Producing an answer leaves no trace

**Ambiguous**: erasure in issue #22 is audited, so producing could be read as needing the same. A
site may also want to evidence that it responded to a request within a deadline.

**Chosen**: no. Reading records does not record anything.

**Why defensible**: an audit trail exists to establish that something changed and who changed it,
and producing an answer changes nothing. Against the case for it, a log of who looked at whose data
is itself personal data about people who did not ask for it, retained indefinitely, which is
exactly what Article XV is pointed at. A site that needs to evidence its response to a request
needs a record of the request and the response, which is a process it runs rather than a gap in
this package.

Raised with Sam at the spec gate as a possible separate feature rather than folded in here, because
an access log over consent data is a real want and is not this feature.

## D5 — No hooks for the host project's own data

**Ambiguous**: the README and Article XIV both mention exposing hooks so a project can join its own
data to the view a person has of their consent, which could be read as belonging here.

**Chosen**: not here. The answer covers what this package holds, and says so.

**Why defensible**: the hooks are R11, aspirational, and gated behind v2 for a reason. Building
them now would mean this feature's correctness depends on host projects implementing something
correctly, and a host project that implements it badly produces an answer that looks complete and
is not. Article XIV names that as worse than no answer. The statement of coverage in FR-015 is the
honest version of the same thing at a hundredth of the cost.

## D6 — The answer's form is left to planning

**Ambiguous**: R3 says "a form a person can actually be shown", which could mean a page, a
downloadable file, or a command an operator runs.

**Chosen**: the specification fixes the properties and not the mechanism: it can be handed to
somebody, it carries the wording in full, it is the same twice, and it is reachable only with the
permission.

**Why defensible**: every one of those properties is testable and none of them depends on the
choice of mechanism, while the choice itself depends on things best decided with the data model in
front of you. Fixing it here would be specification drifting into planning, and the properties are
what a reviewer would check either way.

## Scope raised and left out

**An access log over consent data.** Whether a site can see who produced whose records, and when.
It came out of the question in D4, it is a genuine want for a site that has to demonstrate how it
handles requests, and it is covered by no roadmap item. Raised with Sam separately rather than
widened into this feature, which answers requests rather than governing who may ask.
