# Tasks — 007 Documents that are read but never agreed to

Derived from [plan.md](./plan.md). Task ids are stable and are what `feature-state.json` tracks.
Every task follows Article I: the failing test comes first.

Documentation is not batched into a closing story. Each public name is documented in the story that
introduces it, so the docs check is a real signal at every story boundary.

## Foundational — none

Everything this feature builds on is on main from FS-001 to FS-006. The stories run in sequence:
US-1, then US-2 (plan.md, *Stories and order*).

## US-1 — Publishing a notice nobody is asked to accept (P1, issue #74)

| Id | Task | Done when |
|---|---|---|
| T001 | `tests/test_models.py::TestDocumentKind` — a document created without a kind is `Document.Kind.AGREED`; one created with `kind=Document.Kind.NOTICE` keeps it (FR-001, FR-002). `tests/test_models.py::TestOutstanding` gains: a notice with a version in force is not in `outstanding_for(user)` and `is_outstanding_for(user)` is `False` (scenarios 1, 2); a document created without a kind and with a version in force is outstanding for a user who has not accepted it (scenario 7); with notices and agreed documents mixed, `outstanding_for()` is exactly the agreed documents whose version in force the user has not accepted (SC-001); a notice with only drafts is outstanding for nobody (edge case 1); the query count for `outstanding_for()` is the same with one document as with fifty, notices among them (FR-010, SC-004) | Fails before T002 |
| T002 | `mvp_compliance/models.py` — `Document.Kind` and `Document.kind` per plan.md *The field*; `outstanding_for()` filter and docstring per *What is outstanding*. Migration `0008_document_kind.py` from `makemigrations` | T001 passes; full suite green; `makemigrations --check` clean |
| T003 | `tests/test_migrations.py::TestDocumentKindMigration` — documents, a published version and an acceptance created at `0007_document_slug` are all present and unchanged after migrating to `0008_document_kind`, and every document is `"agreed"` (FR-011, SC-005) | Passes |
| T004 | `tests/test_models.py::TestRecording` gains: `record()` against a notice's version in force and against a notice's superseded version raises `RecordError` and creates nothing (scenario 3); calling it twice raises both times (edge case 4); a user who accepted a document before it was made a notice gets `RecordError` from `record()`, not the old record, and the old record is unchanged; `Acceptance.objects.create()` and `AcceptanceFactory` against a notice's version raise `RecordError`; `Acceptance.objects.bulk_create()` with one notice version in a batch of agreed ones raises and writes none of the batch (FR-004, SC-002) | Fails before T005 |
| T005 | `mvp_compliance/models.py` — `Acceptance.refuse_if_notice()` and its three callers per plan.md *Refusing an acceptance of a notice* | T004 passes |
| T006 | `tests/test_views.py::TestNotice` — a notice's page answers 200 for anonymous and signed-in visitors with the version's stored `html`, its number and in-force date (scenario 4); a signed-in user's page carries no "Agreed on" (scenario 5), including a user whose acceptance was recorded before the document was made a notice (edge case 2); `?version=` with an earlier number shows that version's `html` (scenario 6); the document list beside the wording names both a notice and an agreed document (scenario 8); a notice with only drafts is 404 (edge case 1). `tests/test_models.py::TestVersionPublished` gains: publishing a notice's version sends `version_published` (edge case 5) | Fails before T007 on the "Agreed on" tests only |
| T007 | `mvp_compliance/views.py` — `VersionSubtitleMixin.get_page_subtitle()` per plan.md *The page*; docstring updated | T006 passes |
| T008 | Demo: `seed_demo` gains the "Impressum" notice with one published version; `make_document()` gains `kind`; `SLUGS` gains `impressum`; the landing page links it. `seed_demo` runs on a fresh database | Demo serves `/legal/impressum/` with status 200 |
| T009 | `docs/models.md`: `kind` and `Document.Kind`, a notice is never outstanding, recording against a notice is refused and by which routes. `docs/pages.md`: a notice's page carries no agreement line, linking an impressum from the footer. `CONTEXT.md` **Notice** (FR-014). README feature list. `CHANGELOG.md` `[Unreleased]` Added entry. `en` catalog regenerated (FR-012) | Docs check green on the branch |

## US-2 — Seeing and changing which kind a document is (P2, issue #75)

| Id | Task | Done when |
|---|---|---|
| T010 | `tests/test_admin.py::TestDocumentKindInTheAdmin` — the changelist shows each document's kind in words (scenario 1); the add form saved without touching the kind makes a document people agree to, and saved with "Notice" makes a notice (scenario 2); the change form of a document with published versions changes its kind and no version changes (scenario 3); the changelist's query count is unchanged by the column (#39) | Fails before T011 on the changelist test only |
| T011 | `mvp_compliance/admin.py` — `"kind"` in `DocumentAdmin.list_display` per plan.md *The admin* | T010 passes |
| T012 | `tests/test_models.py::TestChangingTheKind` — through `save()` and through `Document.objects.filter(...).update(kind=...)`, in both directions: the count and content of versions and acceptances are the same before and after (FR-007, SC-003); an agreed document with recorded acceptances made a notice keeps every acceptance and `records.produce()` for that person still lists it (scenario 4); it is then not outstanding for a user who never accepted it (scenario 5); a notice made agreed is outstanding for a user who has not accepted its version in force and not for one who accepted it before it became a notice (scenario 6, edge case 3) | Passes against US-1's code |
| T013 | `docs/authoring.md`: new section *Documents people agree to, and notices* (choosing the kind, changing it, what happens to recorded acceptances); *The documents list* names the kind column. `docs/models.md`: changing the kind from code. `en` catalog regenerated if any string changed | Docs check green on the branch |
