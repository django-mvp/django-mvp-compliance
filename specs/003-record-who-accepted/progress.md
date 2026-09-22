# Progress — 003 The record of who accepted which version

Run narrative. Newest entry last.

## 2026-09-22 — S3 PLAN

Picked off the feature queue as the only row reporting `ready`. The specification merged to main in
pull request #23 on 2026-09-21 at 21:22 UTC, and the issue graph was already built: epic #20,
stories #24 to #28.

FS-001 was delivered after this specification landed, so this specification was re-read against
FS-001's — a comparison of the two documents, not of this document against code. No contradiction:
FS-003 assumes a version that is published, in force or superseded, an at-most-one-in-force rule,
and a stored output fixed at publication, and FS-001 specifies exactly those. The spec's own closing
assumption, that FS-001 was specified and not yet delivered, is the only line that is now out of
date, and it changes nothing this feature builds.

Baseline verified green on `4f55e4d` before anything was written: lint, typecheck, test, build,
conformance and docs all pass.

Written this stage: `research.md`, `plan.md`, `tasks.md`, this file and `feature-state.json`.
`decisions.md` gained D7 to D11 — the five ambiguities the plan had to settle that the specification
did not reach.

The design in one line: one append-only model whose only write route is a manager method, the person
held twice so a record survives its account and still says whose it is, "at most one record per
person per version" as a unique constraint that `get_or_create()` rides, and the outstanding question
answered by one queryset that the single-document form narrows rather than restates.

## 2026-09-22 — S3R DESIGN REVIEW

One reviewer, three lenses, on sonnet. Verdict `approve`, risk low, one verified low finding and one
editorial note; receipts checked green both sides of the dispatch.

DR-001 is a good catch and its evidence was re-verified here against the Django the project actually
resolves. The `on_delete` callable delegating to `SET_NULL` works only because it is an ordinary
function: Django's own `SET_NULL` carries `lazy_sub_objs = True`, the collector reads that attribute
before calling the handler, and a handler that has it leaves `sub_objs` unevaluated, which sends the
field update through `QuerySet.update()` — where this package's guard refuses it. Adding the
attribute by analogy would break the default that says records survive. `research.md` R1, `plan.md`
and T052 all now say so, and US-4's T050 is the test that would notice.

No re-plan: nothing reached the critical or high bar that forces one.
