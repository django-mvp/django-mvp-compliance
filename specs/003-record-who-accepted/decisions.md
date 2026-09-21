# Decisions — 003 The record of who accepted which version

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — Acceptances survive a removed account by default, and a setting says otherwise

**Ambiguous**: an account being closed or tidied up is not an erasure request, but Django's
ordinary behaviour when an account goes is that things attached to it go with it. Two readings are
defensible. Keeping the records honours Article XII, which says an acceptance is never deleted.
Removing them honours Article XV, because a closed account otherwise leaves personal data behind
indefinitely with nobody watching it.

**Chosen**: a setting the host project controls, defaulting to the records surviving.

**Why defensible**: Sam's ruling that a genuinely two-sided question becomes a setting rather than a
guess. The default is the package's own position, which is that evidence outlives convenience: a
site facing a dispute about what somebody agreed to in 2029 is not helped by a record that vanished
when an administrator tidied up an account in 2027, and losing it as a side effect of an unrelated
action is precisely the failure this package exists to prevent. A site that means the opposite sets
the option and gets it, and a site that wants one person's records gone has the deliberate path in
issue #22.

The cost is named rather than hidden: under the default, closing an account does not remove what is
held about that person here, and a project that assumed it did would be wrong. That belongs in the
documentation this feature ships, not only in a setting's docstring.

## D2 — An acceptance can name any published version, not only the one in force

**Ambiguous**: whether the record may point at a superseded version. The obvious reading is that
people accept what is in force, so anything else is a mistake to be refused.

**Chosen**: any published version. Drafts are refused.

**Why defensible**: the race is real rather than theoretical. A person opens the document, reads
it, and a new version is published before they submit. Refusing their acceptance either throws away
something that happened or, worse, records them against wording they never read. Recording what
they actually saw is the only answer consistent with Article XIII, where the stored output is the
evidence. The safety property is preserved elsewhere: what a person has *outstanding* is measured
against the version in force, so that person is simply asked again, which is the correct outcome.

Drafts are refused because a draft has no legal standing at all and accepting one would create a
record pointing at something that can still be edited.

## D3 — Accepting the same version twice leaves one record and does not fail

**Ambiguous**: append-only could be read as meaning every submission produces a row, which would
make a double-submitted form produce two identical records. The alternative reading, that it is an
error, would fail a person who did nothing wrong.

**Chosen**: at most one acceptance per person per version. A repeat succeeds and leaves the record
that already exists.

**Why defensible**: append-only is about facts, not about submissions. Someone clicking twice has
agreed once, so two records would misrepresent what happened as much as an overwrite would. Failing
would push the problem into the flow in R4, where a person meeting an error after agreeing has no
idea whether it worked. Concurrency matters here: two simultaneous submissions have to end at one
record, which is a constraint on the data rather than a check the calling code performs.

## D4 — The outstanding question is answered for every document, and R5 filters it

**Ambiguous**: whether "what does this person have outstanding" should already exclude documents a
site does not enforce. A cookie policy is normally published and never enforced, so including it
looks like a bug.

**Chosen**: this feature answers for every document with a version in force. Enforcement filtering
belongs to R5.

**Why defensible**: enforcement is a policy, and a policy baked into the record layer is a policy
that cannot be changed without touching evidence handling. The account page in R9 and the site-wide
picture in R10 both want the unfiltered answer, so filtering here would force two of the three
consumers to work around it. R5 owns the per-document enforcement decision and applies it to the
answer this feature gives.

## D5 — A surviving record still has to name its person

**Ambiguous**: "the records survive" is only half a statement. A record whose account is gone and
which can no longer say who it belonged to is not evidence, and the two features that read it,
issues #21 and #22, both need to find one person's records as a set.

**Chosen**: a requirement that a surviving record continues to identify the person and continues to
be retrievable with that person's other records. How that identity is held is left to the
implementation.

**Why defensible**: this is the difference between the setting doing what it says and appearing to.
It is a property of the record rather than a design, so it belongs in the specification, while the
mechanism is exactly the kind of decision that should be made with the data model in front of you.
Article XV bears on it directly, because whatever is held for this purpose is personal data that
outlives the account, and it has to be justified where it is defined.

## D6 — Configured removal carries no audit trail, and erasure on request is a separate problem

**Ambiguous**: R3 asks for erasure to be auditable. The setting in D1 also removes records, so it
could be read as needing the same trace.

**Chosen**: no. The setting is a standing behaviour a project configured, not an act about a named
person.

**Why defensible**: an audit trail answers "who decided this, about whom, and when". For a
configured behaviour the answer is the same for everybody and is already recorded in the project's
own configuration history. Erasure on request is the opposite: one person asked, somebody acted,
and that is worth a trace. Designing that trace is issue #22's work, including the question of what
a record of an erasure may itself hold about the person who asked for it.

## Scope raised and left out

**Bringing in acceptances from a previous system.** A site adopting this package usually has
acceptance history already, most often from `django-termsandconditions`. Those are facts that
happened, and appending them breaks no rule here. It is covered by no roadmap item, and it was
raised at intake as a possible gap rather than folded into this feature, because importing records
whose original wording may not be available raises questions this specification does not answer.
