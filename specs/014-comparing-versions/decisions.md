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

**ADR:** none

## D2 — The summary of what changed is a sibling, and nothing here depends on it

**Ambiguous**: the request opens by contrasting itself with the summary, and both serve R6.

**Chosen**: the summary written by whoever prepares a version is #132, built separately. This
feature does not show it, place itself beside it, or assume it exists.

**Why defensible**: the two answer different questions (what the editor chose to say, and exactly
what changed) and can ship in either order. Coupling them would make whichever is built second
reopen the first.

**Revisit if**: both are in place and the page asking to agree needs one arrangement for the two.
That is a question for the later of the two to settle on its prototype.

**ADR:** none

## D3 — Only published versions are compared, and drafts never

**Ambiguous**: the request says "any two published versions", which leaves out drafts, but a person
writing a new version would plainly find a comparison with the version in force useful.

**Chosen**: drafts are out of scope (FR-011). Every page this feature changes is read by people who
must never see a draft.

**Why defensible**: a draft is visible only to the people who manage documents (CONTEXT.md, *Draft*),
and FS-006 already rules that no public page shows one, even to staff. Comparing a draft in the
admin preview is a real but separate need of the compliance editor. It can be raised as its own
request, and it would reuse whatever this feature builds.

**ADR:** none

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

**ADR:** none — follows from Article XII

## D5 — Changes are marked word by word

**Ambiguous**: the request says "what was added and what was removed marked in the text" and does
not say how finely.

**Chosen**: words (FR-003). A moved paragraph shows as removed in one place and added in the other.

**Why defensible**: legal rewording is often a single word, and marking whole paragraphs leaves the
reader to hunt for it. Character-level marks split words and are hard to read. Detecting moved text
is a refinement the request does not ask for, and it can be added later without changing any
address.

**ADR:** none

## D6 — The person's comparison starts from the newest version they accepted

**Ambiguous**: a person may have accepted several versions of one document.

**Chosen**: the newest one they accepted, against the version in force (FR-015, FR-016, FR-019).

**Why defensible**: that is the last wording they agreed to, so its difference from the version in
force is exactly what they have not agreed to. Comparing from their first acceptance would mark
changes they already agreed to.

**ADR:** none

## D7 — "Anyone looking at a person's record" is the person and the staff who produce it

**Ambiguous**: the request does not name the pages.

**Chosen**: the account area's list (FS-008), read by the person, and the page staff use to produce
everything held about a person (FS-004). The page asking to agree (FS-009) is added because it is
where a person who last agreed several versions ago is asked again, which is the case the request
leads with. The copy a person downloads (FS-012) is left alone: it is a file read away from the site,
and a link from it into the site would date it.

**Why defensible**: those are the only places in the package where a person's acceptances are
shown, and the request says a person who agreed two versions ago "has nothing that shows everything
that changed since".

**ADR:** none

## D8 — Comparisons are public, and the same for every reader

**Ambiguous**: the request mentions a person's own record, which is private.

**Chosen**: the comparison itself is open to every visitor (FR-001), and which comparison is
*offered* is what depends on who is reading.

**Why defensible**: both versions are already public on their own pages, so a comparison shows
nothing new. A comparison address that answered differently for different readers could not be
shared or linked from an email.

**ADR:** none

## D9 — The standard library is preferred to a new dependency

**Ambiguous**: producing a word-level comparison of two HTML texts is the one part of the feature
that might tempt a new package.

**Chosen**: the plan starts from Python's standard library (`difflib`) applied to the stored HTML's
text and structure, and adds a dependency only if planning finds the standard library cannot meet
FR-002 to FR-006 and SC-004, with the reason recorded under Complexity Tracking.

**Why defensible**: Articles II and VII ask for a stated justification for any new runtime
dependency. The package makes no outbound request and has few dependencies, and a comparison of two
already-sanitised texts is a well-understood problem the standard library covers.

**ADR:** none at specification. One is due if planning adds a dependency.

## D10 — The specs of the pages that gain an offer are edited when this is built

**Ambiguous**: FS-008 says its list "offers no way to accept" a newer version, and FS-009 says a
summary of what changed "is R6". Neither mentions comparisons.

**Chosen**: this spec states what each of those pages offers. When the feature is built, the scope
lines of FS-004, FS-006, FS-008 and FS-009 that describe what their pages show are brought up to
date in the same pull request, so each still reads as current. #132 is editing FS-002 and FS-009 at
the same time, and the later of the two to merge reconciles FS-009.

**ADR:** none

## D11 — A sketch comes first

**Chosen**: the sketch gate is shut. How marked-up text reads, how a reader chooses the version to
compare with, and how the offer sits on four existing pages are judgements a test cannot settle.

**ADR:** none
