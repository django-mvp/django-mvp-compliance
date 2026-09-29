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

## D3 — Changing the kind needs the document change permission, not the publish permission

**Ambiguous**: the design review (DR-002) pointed out that publishing needs `publish_version`
because making something legally binding is a higher trust level than writing a draft, while the
kind sits on the document form behind `change_document`. An editor who cannot publish could make a
published privacy policy a notice, and it would stop being outstanding for everybody.

**Chosen**: `change_document` is enough. No extra permission check on the kind.

**Why defensible**: the spec asks for the kind to be changeable at any time from the admin (FR-007,
FR-009) and names no permission beyond the admin's own, so gating it would be a requirement the spec
does not state. The kind changes no wording and no record: every acceptance stays as it was
(FR-007) and turning it back restores the answer exactly (edge case 3), so it is a document setting
rather than a publication. Nothing blocks a request on "outstanding" yet (R4 and R5 are unbuilt),
so today the change has no effect on any user. This is raised with the maintainer in the plan
notification. If they want it behind `publish_version` once a version is published, that is a
change to FR-009 and goes through a delta brief.

**Revisit if**: R5 makes "outstanding" block requests, at which point turning a document into a
notice lets people through without accepting it.

**ADR:** none — follows from the spec's own wording; revisited with R5, which owns enforcement.

## D4 — ADR 0009 is amended, not superseded

**Ambiguous**: ADR 0009's decision sentence says `outstanding_for()` returns every document with a
version in force that the person has not accepted. FR-003 leaves notices out. The design review
(DR-001) found that the ADR's reasoning, which is about keeping enforcement policy out of the
answer, still holds.

**Chosen**: amend ADR 0009 in place so its decision says a notice is never outstanding, with the
reason, and leave its reasoning unchanged. No new ADR.

**Why defensible**: a notice is not a document the site chose not to enforce. Nobody can accept one,
so leaving it out is about what the answer means, not a policy on top of it. The ADR's argument
against filtering (callers want the unfiltered answer, one rule in one place) applies unchanged to
enforcement and does not apply to a kind of document that nobody can accept.

**Revisit if**: a caller ever needs notices in the answer. None of the three the ADR names does.

**ADR:** docs/adr/0009-outstanding-is-answered-for-every-published-document.md (amended)

## D5 — Three existing tests gain the new field

**Ambiguous**: adding `kind` changed three tests written before it existed.
`TestDocument::test_document_holds_no_wording` asserts the document's exact field set, and two tests
in `TestDocumentSlugInTheAdmin` post the change form with only a name and a slug. The form now has
a required `kind` select, so a browser always posts it, but these hand-built posts did not.
Changing a test this feature did not write is normally refused.

**Chosen**: authorised by the orchestrator at US-1 acceptance. The field-set assertion lists `kind`,
and the two posts carry `"kind": "agreed"`. No assertion was changed or weakened.

**Why defensible**: each test still proves what it was written to prove: that a document holds no
wording, and how the slug behaves before and after publication. The edits only bring each test's
inputs up to date with the document as it now is. Weakening them, for example by making `kind`
optional on the form, would change behaviour to suit a test.

**ADR:** none — a test maintenance ruling local to this feature.

## D6 — R5 stays open on the roadmap

**Ambiguous**: `roadmap-status` marked R5 delivered, because #65 is the only issue filed under R5.
The spec says this feature is one part of R5: per-document enforcement and applying the check across
the site are the rest of it and have no issues yet.

**Chosen**: R5's status line stays `feature`. R2 and R3, which the same run marked delivered from
FS-001 to FS-006, keep the delivered status, with their briefs rewritten in the delivered form.

**Why defensible**: a roadmap line reading "delivered" for an item whose main deliverable, enforcement,
is not built would tell the next planner there is nothing left to do. The tool derives delivery from
the issues filed so far, and that derivation is only as complete as the decomposition.

**Revisit if**: R5 is decomposed into the rest of its issues. The tool will then derive its status
correctly.

**ADR:** none — a roadmap bookkeeping correction, not an architectural decision.
