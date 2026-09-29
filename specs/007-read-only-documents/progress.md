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

## 2026-09-29T21:20Z · Implementer US1 · T004

Did: `TestRecording` gains seven tests. `record()` against a notice's version in force and its
superseded one; twice in a row; a user who accepted before the document became a notice (`RecordError`,
old record unchanged); a version whose `document` instance was loaded before the kind changed;
`Acceptance.objects.create()` and `AcceptanceFactory`; `bulk_create()` with one notice in a batch of
two (none written); and `bulk_create()` of agreed documents still works.
Verified: `uv run pytest tests/test_models.py::TestRecording -q` gave 6 failed, 10 passed, each
failure `DID NOT RAISE RecordError`.
Next: T005.
Watch: the stale-instance test is what keeps the check reading the database rather than `version.document`.

## 2026-09-29T21:30Z · Implementer US1 · T005

Did: `Acceptance.refuse_if_notice(version_ids)` (one query, reads the database), called by
`record()` after the "never published" refusal and before `get_or_create()`, by `Acceptance.save()`
after the "already recorded" guard, and by `AcceptanceQuerySet.bulk_create()` before anything is
written. `en` catalog gained the refusal message; the catalog tool marked it fuzzy against an
unrelated entry, so I corrected the entry by hand.
Verified: `uv run pytest tests/test_models.py::TestRecording tests/test_models.py::TestAcceptanceImmutability -q`
gave 23 passed; `tests/test_admin.py::TestUserFacingStrings` passes.
Next: T006.
Watch: `Acceptance._base_manager.bulk_create()` is a plain manager and is not covered, by design.

## 2026-09-29T21:40Z · Implementer US1 · T006

Did: `tests/test_views.py::TestNotice` (200 for anonymous and signed-in with stored html, number and
date; no "Agreed on" for a signed-in user on the current and earlier versions; the same after an
acceptance recorded before the document became a notice, on the earlier `?version=` too; an earlier
version's own html; the side list carries a notice and an agreed document; draft-only notice is 404)
and `TestVersionPublished::test_publishing_a_notices_version_is_announced_too`.
Verified: `uv run pytest tests/test_views.py::TestNotice tests/test_models.py::TestVersionPublished -q`
gave 1 failed, 16 passed; the one failure is the "Agreed on" test for an acceptance from before the
change, the only case where the line can appear at all.
Next: T007.
Watch: a notice made from a document nobody accepted cannot show the line before T007 either, so
only the earlier-acceptance test is red.

## 2026-09-29T21:45Z · Implementer US1 · T007

Did: `VersionSubtitleMixin.get_page_subtitle()` returns the version line alone when the version's
document is a notice, before it looks for an acceptance. The mixin's docstring now says it is used
by the document's page only (it named a version's page, which does not use it) and mentions the
exception.
Verified: `uv run pytest tests/test_views.py -q` gave 65 passed, the query-count tests among them
(`version.document` is already loaded, so the check costs no query).
Next: T008.
Watch: none.

## 2026-09-29T21:55Z · Implementer US1 · T008

Did: `seed_demo` seeds an "Impressum" notice (slug `impressum`, one published version);
`make_document()` takes `kind`, defaulting to a document people agree to; `SLUGS` gains `impressum`;
the landing page links it and lists it among the seeded documents. No test: the demo is not part of
the package and has none.
Verified: against a throwaway sqlite database outside the repo (removed afterwards), a fresh
`migrate` and `seed_demo` ran clean and a second `seed_demo` reported the impressum already seeded.
Through the test client, `/legal/impressum/` answered 200, for the seeded acceptor signed in it
carried no "Agreed on" while `/legal/privacy-policy/` did, and `/` linked the impressum. No dev
server was started.
Next: T009.
Watch: none.

## 2026-09-29T22:15Z · Implementer US1 · T009

Did: ADR 0009 amended in place (its Decision says a notice is never outstanding because nobody can
accept one, marked amended 2026-09-29; the Why is untouched). `docs/models.md`: a *The kind*
section under `Document`, *Outstanding* says a notice is left out, the "deliberately unfiltered"
sentence now says the answer ignores enforcement and not kind, and *Acceptance* lists the routes
that refuse (`record()`, `create()` and a new save, `bulk_create()`, the async forms) and names
`_base_manager.bulk_create()` as not covered. `docs/pages.md`: a notice's page has no agreement line,
linking an impressum from the footer. `CONTEXT.md` **Notice**, README feature list and Models
section, CHANGELOG `[Unreleased]` Added entry. The `en` catalog regenerated; it has no new string
beyond T002 and T005, and nothing is fuzzy.
Verified: `uv run pytest tests/test_admin.py::TestUserFacingStrings -q` passes. The full verify runs
once, at the end of the story.
Next: full verify, then the report.
Watch: the two admin tests and one model test that T002 cannot keep green are for Forge to triage.

## 2026-09-29T22:25Z · Implementer US1 · full verify

Ran `forge verify --repo … --base origin/main`: conformance, docs, lint, typecheck and build pass;
`uv:test` fails (exit 1) on three tests written before `kind` existed, which I may not edit:
`tests/test_models.py::TestDocument::test_document_holds_no_wording` (field set now includes
`kind`) and two admin tests that post the document change form with no `kind`
(`TestDocumentSlugInTheAdmin::test_an_unpublished_documents_slug_can_be_edited`,
`::test_a_post_carrying_a_different_slug_leaves_a_published_slug_alone`). A plain
`uv run pytest tests -n auto --dist loadscope` gave 3 failed, 420 passed. Each needs one line added
to the test (`"kind"` in the set; `"kind": "agreed"` in the posted data). Forge triages.
