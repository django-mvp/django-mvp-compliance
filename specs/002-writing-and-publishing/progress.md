# Progress — 002 Writing and publishing a document without a developer

Run narrative. Newest entry last.

## 2026-09-22 — S3 PLAN

Picked up off the feature queue as `ready`. Branch `002-writing-and-publishing` cut from
`origin/main` at `4f55e4d`, with the stale local branch left over from the specification run
deleted first after confirming its `specs/` content was identical to what merged as #13.

**Spec re-read against FS-001, the one feature delivered since this specification landed.** No
contradiction. FS-002's specification was written the same day and with FS-001's in hand — it names
it as a dependency throughout and adds no state to either model — and FS-001's `spec.md` has not
been touched since. The one place they meet is FR-004, where this feature's toolbar has to agree
with the allow list FS-001 applies at publication; the allow list is wider than the toolbar, which
is agreement rather than conflict, and T018 tests it in both directions.

Baseline verified green on the branch before planning: conformance, lint, typecheck, 65 tests and
build.

Research settled three things worth naming. The specification itself decides the editor — US-3
scenario 5 compares the editor's inline display with the preview, which needs an editor that has
one. EasyMDE ships no icons despite writing Font Awesome class names into every button, so the
icons are ours. And the preview reads the stored row rather than the editor's buffer, because that
is the only design under which SC-004 is true by construction.

`decisions.md` gained D8 to D12 and ADR verdicts for D1 to D7, which the specification run left
open.

## 2026-09-22 — S3R DESIGN_REVIEW

One reviewer, three lenses, one round. Verdict `request_changes`: one high, two medium, one low,
all `verified`. Every finding checked against its own stated evidence before it was applied.

Three became plan edits:

- The version form had no declared field list, and `html` — the evidence `publish()` produces —
  carries no `editable=False`, so it could have been exposed as a postable field. `VersionForm`
  now declares `fields = ["document", "markdown"]` and the admin marks the rest read-only, with a
  test asserting the form's field names are exactly those two.
- All five stories add to the same `admin.py`, so they are sequentially dependent. `tasks.md` now
  says so rather than leaving it to be discovered at convergence.
- The publish view planned to catch an exception `publish()` cannot raise. Verified against the
  model: both refusals raise `PublishError`, and the save inside `publish()` runs while the stored
  row is still a draft, so the immutability guard returns first. The second branch is gone.

The high finding is not a plan fault and was not applied. This specification's edge case about
deleting a document that holds only drafts contradicts FS-001's D8 and its accepted ADR 0002. No
requirement in this feature depends on it, the behaviour it asks for is reachable in one extra
step, and building it would mean overriding Django's deletion collector to route around the guard
that ADR exists to keep. Recorded as D13 and raised with Sam; the delivered behaviour stands
meanwhile.
