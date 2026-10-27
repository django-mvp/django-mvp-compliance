# Decisions — 014 Comparing two versions of a document

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. The feature request (#133) was read and specified without a round of questions, so
each place it was silent was filled with a reading and is listed here. Each entry names what was
unclear, what was chosen, and why the choice is defensible. Any of them can be overruled in review
of the specification.

## D1 — It is a feature, and one of its own

**Ambiguous**: comparing versions sits next to the document pages (FS-006), and one new way inside
an existing feature would be added to that feature's spec instead.

**Chosen**: a new specification. After it, a reader can compare two versions, a person can see
everything that changed since they last agreed, and staff can see how an old acceptance differs
from what is in force. Those are several new ways, on four existing pages, for three different
people, and no existing spec describes any of them.

**Why defensible**: the roadmap item (R6) was widened on 2026-10-26 to name the comparison as its
own part, and the request names all three readers.

**ADR:** none — a ruling on how this work was run, not on the code

## D2 — The summary of what changed is a sibling, and nothing here depends on it

**Ambiguous**: the request opens by contrasting itself with the summary, and both serve R6.

**Chosen**: the summary written by whoever prepares a version is #132, built separately. This
feature does not show it, place itself beside it, or assume it exists.

**Why defensible**: the two answer different questions (what the editor chose to say, and exactly
what changed) and can ship in either order. Coupling them would make whichever is built second
reopen the first.

**Revisit if**: both are in place and the page asking to agree needs one arrangement for the two.
That is a question for the later of the two to settle on its prototype.

**ADR:** none — a scope boundary between two pieces of work; nothing in the code depends on it

## D3 — Only published versions are compared, and drafts never

**Ambiguous**: the request says "any two published versions", which leaves out drafts, but a person
writing a new version would plainly find a comparison with the version in force useful.

**Chosen**: drafts are out of scope (FR-011). Every page this feature changes is read by people who
must never see a draft.

**Why defensible**: a draft is visible only to the people who manage documents (CONTEXT.md, *Draft*),
and FS-006 already rules that no public page shows one, even to staff. Comparing a draft in the
admin preview is a real but separate need of the compliance editor. It can be raised as its own
request, and it would reuse whatever this feature builds.

**ADR:** docs/adr/0030-a-comparison-is-computed-from-the-stored-html-and-never-stored.md

## D4 — What is compared is the stored HTML

**Ambiguous**: a version holds both the Markdown a person wrote and the HTML rendered from it at
publication.

**Chosen**: the stored HTML (FR-005), with the structure of the text kept and the changes marked
within it (FR-004), and nothing added to it but the marks (FR-006).

**Why defensible**: Article XII forbids rendering Markdown at request time, and the stored HTML is
what a reader was served and what an acceptance points at (CONTEXT.md, *Version*). Comparing the
Markdown and then rendering the result would show readers a text that was never served. Producing
the marked-up result from two sanitised texts is not rendering Markdown, but it does create new
markup, so FR-006 makes the safety of the output a requirement rather than an assumption.

**ADR:** docs/adr/0030-a-comparison-is-computed-from-the-stored-html-and-never-stored.md

## D5 — Changes are marked word by word

**Ambiguous**: the request says "what was added and what was removed marked in the text" and does
not say how finely.

**Chosen**: words (FR-003). A moved paragraph shows as removed in one place and added in the other.

**Why defensible**: legal rewording is often a single word, and marking whole paragraphs leaves the
reader to hunt for it. Character-level marks split words and are hard to read. Detecting moved text
is a refinement the request does not ask for, and it can be added later without changing any
address.

**ADR:** docs/adr/0030-a-comparison-is-computed-from-the-stored-html-and-never-stored.md

## D6 — The person's comparison starts from the newest version they accepted

**Ambiguous**: a person may have accepted several versions of one document.

**Chosen**: the newest one they accepted, against the version in force (FR-015, FR-016, FR-019).

**Why defensible**: that is the last wording they agreed to, so its difference from the version in
force is exactly what they have not agreed to. Comparing from their first acceptance would mark
changes they already agreed to.

**ADR:** none — a rule of two pages, stated in the spec (FR-015, FR-016); nothing else inherits it

## D7 — "Anyone looking at a person's record" is the person themselves

**Ambiguous**: the request does not name the pages.

**Chosen**: the account area's list (FS-008), read by the person, and the page asking to agree
(FS-009), where a person who last agreed several versions ago is asked again, which is the case the
request leads with. The page staff use to produce everything held about a person (FS-004) offers no
comparison: the maintainer ruled it out on reviewing the prototype, and asked instead for each
acceptance's version number there to link to that version's page in the admin. The copy a person
downloads (FS-012) is left alone: it is a file read away from the site, and a link from it into the
site would date it.

**Why defensible**: a person's own record is where the question "what changed since I agreed" is
asked. Staff can open any comparison from the document's page if they need one.

**ADR:** none — which pages offer a comparison is the spec's scope, not an architectural rule

## D8 — Comparisons are public, and the same for every reader

**Ambiguous**: the request mentions a person's own record, which is private.

**Chosen**: the comparison itself is open to every visitor (FR-001), and which comparison is
*offered* is what depends on who is reading.

**Why defensible**: both versions are already public on their own pages, so a comparison shows
nothing new. A comparison address that answered differently for different readers could not be
shared or linked from an email.

**ADR:** none — follows from versions already being public on their own pages; local to the comparison page

## D9 — The standard library is preferred to a new dependency

**Ambiguous**: producing a word-level comparison of two HTML texts is the one part of the feature
that might tempt a new package.

**Chosen**: the plan starts from Python's standard library (`difflib`) applied to the stored HTML's
text and structure, and adds a dependency only if planning finds the standard library cannot meet
FR-002 to FR-006 and SC-004, with the reason recorded under Complexity Tracking.

**Why defensible**: Articles II and VII ask for a stated justification for any new runtime
dependency. The package makes no outbound request and has few dependencies, and a comparison of two
already-sanitised texts is a well-understood problem the standard library covers.

**ADR:** docs/adr/0030-a-comparison-is-computed-from-the-stored-html-and-never-stored.md

## D10 — The specs of the pages that gain an offer are edited when this is built

**Ambiguous**: FS-008 says its list "offers no way to accept" a newer version, and FS-009 says a
summary of what changed "is R6". Neither mentions comparisons.

**Chosen**: this spec states what each of those pages offers. When the feature is built, the scope
lines of FS-004, FS-006, FS-008 and FS-009 that describe what their pages show are brought up to
date in the same pull request, so each still reads as current. #132 is editing FS-002 and FS-009 at
the same time, and the later of the two to merge reconciles FS-009.

**ADR:** none — a documentation task carried out in this pull request

## D11 — A sketch comes first

**Chosen**: the sketch gate is shut. How marked-up text reads, how a reader chooses the version to
compare with, and how the offer sits on four existing pages are judgements a test cannot settle.

**ADR:** none — a ruling on how this work was run

## D12 — Links to a comparison are worded the same everywhere

**Chosen**: every link that opens a comparison uses one short, generic wording, with no version
numbers in it. Ruled by the maintainer on reviewing the prototype ("far too detailed").

**Why defensible**: the comparison itself names both versions, so the link needs to say only where
it leads.

**ADR:** none — a wording ruling local to four templates

## D13 — The staff page links a version only for someone who may view it

**Ambiguous**: the maintainer asked for each acceptance's version on the staff page to link to the
version in the admin. That page is open to anyone holding the permission to produce what is held,
which on its own does not let them view versions (ADR 0011).

**Chosen**: the link is drawn only when the reader may view versions. Otherwise the text stays as
it was.

**Why defensible**: a link that answers "forbidden" is a broken link.

**ADR:** none — local to the staff page's template

## D14 — A comparison's address always names both versions

**Chosen**: `from` and `to` are both required, and an address missing either answers "not found".
The sketch's default for a bare address is removed.

**Why defensible**: FR-009 asks for an address built from the two versions, so that it keeps
showing the same comparison. A bare address would change meaning with every publication, and
nothing in the package links to one.

**ADR:** none — the address shape is documented in docs/pages.md and pinned by tests; it constrains nothing beyond the page

## D15 — The staff page learns a version's key from the answer itself

**Chosen**: each entry in the produced answer gains the version's key, `version_id`. The produced
answer already loads the version, so no query is added, and the copy a person downloads names its
columns and is unchanged.

**Why defensible**: looking the version up again in the admin by document name and number costs a
query and repeats what the answer already knew.

**ADR:** none — one field on one dataclass, recorded in the CHANGELOG

## D16 — Two versions that differ only in markup have no differences to show

**Ambiguous**: a link's address can change while every word stays the same. The comparison marks
words, so it would show such a text with nothing marked.

**Chosen**: two versions are "the same" when their words are, with tags removed, and the page says
there are no differences.

**Why defensible**: FR-010 asks the page to say so whenever it would mark nothing. Showing an
unmarked text without saying why leaves the reader hunting. Marking a changed address is a
different requirement, and would go back through the specification.

**ADR:** none — a behaviour of the comparison stated in the spec (FR-010) and pinned by tests

## D17 — The design review's findings

All five were taken as plan edits: a window bounding the pairing pass (high), the newer version's
wrappers as the only wrappers with a balance test, a quote-aware tag pattern, `same` comparing
words (D16), and two more checks on the comparison page. The review also found that the sketch's
document page reads the version in force with a query of its own, which is deleted.

**ADR:** none — a record of plan edits; the lasting ones are in ADR 0030
