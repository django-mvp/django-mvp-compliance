# Decisions — 009 Asking a signed-in person to agree to what is outstanding

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. The feature request (#86) was read and specified without a round of questions, so
each place it was silent was filled with a reading and is listed here. Each entry names what was
unclear, what was chosen, and why the choice is defensible. Any of them can be overruled in review
of the specification.

## D1 — The request is read as one page, and the page stops nobody

**Ambiguous**: the request says a person "should be shown that version in full and asked to
agree", and also that deciding when a person is sent there is separate work. It does not say
whether the page itself holds a person until they agree.

**Chosen**: the feature is a page a person is sent to or opens. It records and returns. It can be
left like any other page, and leaving records nothing (FR-024). Holding a person until they agree
is enforcement, which is R5 (#87).

**Why defensible**: #87 owns the site-wide check, the addresses that stay reachable and whether a
document is enforced at all. A page that trapped a person would decide enforcement here, for every
document, before that feature has said which documents are enforced.

**Revisit if**: R5 needs the page to behave differently for an enforced document than for one left
to the person's own time.

## D2 — The page asks about everything outstanding, not only what is enforced

**Ambiguous**: #87 will let a compliance editor decide, per document, whether an outstanding
acceptance stops a person. The request does not say whether the page lists only documents that
stop a person.

**Chosen**: every document outstanding for the person is on the page, as FS-003 answers the
question today (FR-001). The person is sent on when nothing is outstanding (FR-008).

**Why defensible**: enforcement per document does not exist yet, and FS-003 deliberately answers
for every published document people agree to (ADR 0009). A document left for a person to accept in
their own time still needs somewhere to be accepted, and this is the only such place.

**Revisit if**: R5 is specified. It may narrow what a person must clear before being sent on to
the enforced documents, with the rest offered and not required. That would change FR-008 and
FR-012 and should be made there as an amendment to this spec.

## D3 — Each document is agreed to separately, in one submission

**Ambiguous**: "they deal with all of them in one sitting" could mean one answer for everything, or
one answer per document given together.

**Chosen**: one answer per document, one submission (FR-003).

**Why defensible**: an acceptance is the record that a person agreed to one version of one
document. A single answer covering several documents is weaker evidence for each. One submission
still meets "one sitting instead of being sent round once per document".

**Revisit if**: the prototype shows that separate answers make the page harder to complete than a
person will tolerate.

## D4 — Agreeing to part of what is shown is recorded

**Ambiguous**: the request does not say what happens when a person agrees to some documents and
not others.

**Chosen**: the ones agreed to are recorded and the page returns with the rest (FR-012).

**Why defensible**: the alternative throws away an agreement the person gave. The record would then
say less than what happened, and the person would have to give the same answer again.

**Revisit if**: R5 makes all enforced documents a single condition of using the site, where a
partial answer has no use.

## D5 — One submission's acceptances are stored together or not at all

**Ambiguous**: "if no acceptance was stored, the person has not agreed" covers one document. With
several, a failure could leave some stored and some not.

**Chosen**: all or none (FR-010). After a failure nothing from that submission exists, and the
person is told their agreement was not recorded.

**Why defensible**: the person can be told one true thing. A half-stored submission needs a message
that says which documents were recorded, and a second attempt that has to work out the difference.
Submitting again costs nothing, because FS-003 keeps one acceptance per person and version.

**Revisit if**: never, short of a change to what FS-003 guarantees about repeats.

## D6 — Whether a person is let through is read from the stored records

**Ambiguous**: the request says the person is "shown the page again instead of being let through
with nothing behind them", without saying what the page relies on to know.

**Chosen**: after every submission the page asks again what is outstanding for the person and
sends them on only when the answer is nothing (FR-008). This covers a failure that raised no error
(US-2, scenario 5).

**Why defensible**: the roadmap calls this "the difference between a record you can rely on and a
record that is merely usually correct". A decision taken from the submission, or from the absence
of an error, can be wrong while the records are right. A decision taken from the records cannot.

**Revisit if**: never. It is the point of the feature.

## D7 — A version replaced while a person was reading it is not recorded

**Ambiguous**: a new version can be published between a person opening the page and submitting.

**Chosen**: nothing is recorded for the replaced version, and the person is shown the page again
with the version now in force (FR-005).

**Why defensible**: an acceptance of the new version would be of wording they never saw. An
acceptance of the old one is permitted by FS-003 and would be true, but it settles nothing, since
the document stays outstanding and they are asked again at once. Leaving it out keeps the record
to answers that were worth asking for.

**Revisit if**: a project needs evidence that a person agreed to a version in its last minutes in
force.

## D8 — The destination is restricted to the same site, with a default the project sets

**Ambiguous**: "they carry on to wherever they were going" does not say what happens when no
destination was given, or when the one given is unusable.

**Chosen**: only an address on the same site is followed. Anything else, a missing one, or the
page's own address, is replaced by a default the project can set, and the package supplies one
that works with no setting (FR-016, FR-017).

**Why defensible**: the destination arrives in the request, so anybody who builds a link to the
page can write it. Following it to another site would let the page be used to send people
anywhere. The name of the setting and the default's value are left to the plan.

**Revisit if**: a project needs to return people to another of its own domains.

## D9 — A person with nothing outstanding is sent straight on

**Ambiguous**: "a person with nothing outstanding never sees any of this" could be met by the page
answering "not found", by an empty page, or by sending the person on.

**Chosen**: they are sent on to their destination, or the default (FR-018).

**Why defensible**: a developer can then send everybody to the page without checking first, and R5
can rely on the same behaviour. "Not found" would break a link a project legitimately made, and an
empty page is the thing the request says nobody should see.

**Revisit if**: never, unless R5 needs a different answer for accounts it lets past.

## D10 — Not agreeing leaves no record

**Ambiguous**: the roadmap says "what they do next is recorded", which could include a refusal.

**Chosen**: only an acceptance is recorded. A person who does not agree leaves no record (FR-024).

**Why defensible**: CONTEXT.md defines an acceptance as a historical fact, and the package has no
record of a refusal. The request itself speaks only of recording the acceptance. A refusal record
would be new personal data about a person who did nothing, which Article XIV would need declared.

**Revisit if**: R10 needs to tell "was asked and did not agree" from "was never asked".

## D11 — Nothing else in the package links to the page

**Ambiguous**: the account area's list (FS-008) already tells a person when a newer version is in
force that they have not accepted, and its spec says the asking page "may link from this page".

**Chosen**: no link is added here. The list and the document pages are unchanged.

**Why defensible**: the request does not ask for it, and it is one link that can be added to
FS-008's spec on its own once the page exists. Adding it here would change a delivered feature
inside a specification about another.

**Revisit if**: the prototype shows the page is too hard to find before R5 is delivered.

## D12 — The page is served with the package's other pages, and its address is reserved

**Ambiguous**: the request does not say where the page lives.

**Chosen**: beside the document pages, under whatever prefix the project mounts them at. No
document may take the slug that would collide with it (FR-021, FR-022). The address itself is left
to the plan.

**Why defensible**: it is how FS-008 placed its list, and the same refusal already exists for that
address. The page is not part of the account area: a person is sent here on their way somewhere
else, and it does not belong in a menu.

**Revisit if**: the package gains enough fixed addresses that a prefix no slug can match becomes
cheaper than a growing set of reserved slugs, which FS-008's D3 already anticipates.

## D13 — The page is prototyped before it is planned

**Ambiguous**: whether this feature needs its screen looked at before the implementation is
planned.

**Chosen**: yes. How several long documents and their requests to agree are arranged on one page,
and how a failure is announced, are judgements of the eye. The specification fixes no wording and
no appearance, and the last assumption in `spec.md` says so.

**Why defensible**: it is a new page with a form on it, and the feature exists to serve G5, which
no test can assert. FS-008 went the same way, and its prototype changed the specification.

**Revisit if**: never for this feature.

## D14 — The page lists the documents and links to their wording

**Ambiguous**: the request says a person "should be shown that version in full". The first
prototype put each document's wording on the page, in a scrolling region when several were
outstanding.

**Chosen**: the maintainer ruled, on the prototype, that the page does not show documents in full.
Each outstanding document is one entry: its name, its version, a link to that version's own page
and the request to agree. FR-002, FR-005, SC-003 and the scenarios that spoke of wording on the
page were rewritten to say so.

**Why defensible**: it is the maintainer's ruling on the screen he was asked to judge. Every
published version already has a page that serves its stored wording, so nothing has to be
rendered twice, and the link names the exact version the acceptance will point at. The record
still says which version a person agreed to. It does not say they read it, and it never did: a
scrolling region proved no more.

**Revisit if**: a project needs evidence that the wording was opened before the agreement was
given. That would be new tracking and new personal data, and would need its own decision.

## D15 — "Required" and "optional" are the two words for the two kinds

**Ambiguous**: the review used both "required" and "mandatory" for a document a person cannot
continue without.

**Chosen**: "required" and "optional", everywhere on the page.

**Why defensible**: one word per meaning is what a translator needs, and the alert the review
dictated already says "required". Which documents are required is the site-wide check's to decide
(#87). The prototype fakes it.

**Revisit if**: the maintainer meant "mandatory" to be the term.
