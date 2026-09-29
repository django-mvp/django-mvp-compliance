# Progress — 007 Documents that are read but never agreed to

The running log of this feature's implementation run. The ledger (`feature-state.json`) is the
machine record; this is the readable one.

---

## 2026-09-29 — S3 PLAN

Picked off the feature queue for this repo, with no feature delivered since the specification
landed, so there was nothing to re-read it against. Branch `007-read-only-documents` cut from
`origin/main` at `4e7973f`, which carries the specification merged in #73. Verify green on that
commit: conformance, docs, lint, typecheck, tests, build.

Plan, research and tasks written. Two stories, run in sequence: US-1, then US-2. Every functional
requirement and success criterion maps to at least one task. No critical findings.

## 2026-09-29 — S3R DESIGN REVIEW

One reviewer, three lenses, receipts green. Verdict: approve, with no critical or high findings.
Applied as plan and task edits: DR-001 (amend ADR 0009 and the "deliberately unfiltered" sentence in
T009, D4), DR-003 (exclude notices rather than filter to agreed), DR-004 (one `refuse_if_notice`
over version ids), DR-005 (dropped a query-count clause the existing changelist test covers),
DR-006 (the `?version=` page of an earlier version also carries no agreement line). DR-002 (who
may change the kind) ruled in D3 and raised in the plan notification.

## 2026-09-29T21:00Z · Implementer US1 · T001

Did: `TestDocumentKind` (default agreed, notice kept) and six `TestOutstanding` cases: a notice with a
version in force is not outstanding, a document created without a kind still is, a mix of notices
and agreed documents gives exactly the unaccepted agreed ones, a notice with only drafts is
outstanding for nobody, an unknown kind value still counts as outstanding, and the query count is
the same at two documents as at fifty with notices among them.
Verified: `uv run pytest tests/test_models.py::TestDocumentKind tests/test_models.py::TestOutstanding -q`
gave 7 failed, 8 passed, every failure the missing `Document.Kind` / `kind`.
Next: T002.
Watch: no test for "kind is not indexed": it could only fail by someone changing the decision.

## 2026-09-29T21:05Z · Implementer US1 · T002

Did: `Document.Kind` and `Document.kind`, `outstanding_for()` excludes notices (docstrings updated),
migration `0008_document_kind` (one `AddField`), `en` catalog regenerated for the four new strings
(the catalog test needs them; msgstr filled the way the existing entries are).
Verified: the two T001 classes pass (15 passed); `makemigrations --check --dry-run` clean; ruff,
mypy and the other pre-commit hooks pass. The whole suite: 3 failed, 405 passed. The three failures
are older tests that describe the model as it was before, and I may not edit them:
- `tests/test_models.py::TestDocument::test_document_holds_no_wording` expects the concrete fields
  to be exactly `{"id", "name", "slug"}`; it needs `"kind"` added.
- `tests/test_admin.py::TestDocumentSlugInTheAdmin::test_an_unpublished_documents_slug_can_be_edited`
  and `::test_a_post_carrying_a_different_slug_leaves_a_published_slug_alone` post a change form
  with only `name` and `slug`; `kind` is a required form field, so the form is invalid (200, not
  302). Each needs `"kind": "agreed"` in the posted data.
Next: T003. T002 is marked blocked for Forge to triage those three one-line edits; the code is done.
Watch: nothing in the model can avoid this: a required field on the change form is the design.

## 2026-09-29T21:12Z · Implementer US1 · T003

Did: `TestDocumentKindMigration` builds two documents, a published version and an acceptance at
`0007_document_slug` with the historical `.objects.create()` (never `bulk_create`), migrates to
`0008_document_kind`, and checks every document is `"agreed"` and the version and acceptance are
unchanged. The database is put back at the latest migration in a `finally`.
Verified: `uv run pytest tests/test_migrations.py -q` gave 4 passed.
Next: T004.
Watch: passes on arrival by design (its done-when is "Passes"); T002 already carried the migration.
