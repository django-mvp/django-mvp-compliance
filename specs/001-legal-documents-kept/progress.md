# Progress — 001 Legal documents kept as versioned records

Run narrative. Newest entry last.

## 2026-09-21 — S3 PLAN

Picked off the feature queue as the only row reporting `ready`. The specification merged to main in
pull request #6 at 17:29 UTC and the issue graph was already built: epic #4, stories #7 to #11. No
feature has been delivered in this repository since the specification landed, so the specification
was not re-read against later ones.

Baseline verified green on `1f56542` before anything was written: lint, typecheck, test, build and
conformance all pass.

Written this stage: `research.md`, `plan.md`, `tasks.md`, this file and `feature-state.json`.
`decisions.md` gained D8, D9 and D10 — the three ambiguities the plan had to settle that the
specification did not reach.

The design in one line: two models, publishing as a method that renders once and freezes the row,
"one version in force" as a partial unique index rather than application logic, and immutability
enforced on all four write routes with the manager declared `use_in_migrations` so a migration gets
the same refusal.
