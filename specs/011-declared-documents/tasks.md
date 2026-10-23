# Tasks — 011 Declaring the documents a site links to

Derived from [plan.md](./plan.md). Task ids are stable.
Every task that changes behaviour follows Article I: the failing test comes first. Tests find
elements by fixture data, id or `data-` hook, never by wording, and assert an error by its type
and by the slugs it names, never by its sentence.

Documentation is not batched into a closing story. Each public name is documented in the story that
introduces it.

Tests that need declarations set `MVP_COMPLIANCE_DOCUMENTS` with `override_settings` or the
`settings` fixture. `tests/settings.py` declares nothing.

US-1 is built before US-2 (plan.md, Order).

## US-1 — Declaring the documents a site links to (P1, issue #114)

| Id | Task | Done when |
|---|---|---|
| T001 | `tests/test_management.py::TestCreateDeclaredDocuments` — with two declarations and no documents, calling the receiver creates both with the declared slug and name, no version, and the `kind` and `enforced` of `Document()` built with neither given (scenario 1, FR-002, FR-003); a declared document with no version answers 404 at its page, is absent from `Document.objects.in_force()` and from `outstanding_for(user)` (scenario 2, FR-007); a second call creates nothing and leaves name, kind and enforced as they were, including after they were changed (scenarios 4 and 6, FR-004); a document that already has the declared slug, with a published version and an acceptance, is left with the same field values and the same version and acceptance rows (scenario 5, FR-005); dropping a declaration and calling again leaves the document (scenario 7, FR-006); with nothing declared the call creates nothing (scenario 11, FR-009); with `apps` lacking the model the call does nothing; a declared document given a published version through `Version.publish()` answers its page with that version (scenario 3) | Fails before T002 |
| T002 | `mvp_compliance/models.py` `declared_documents()`; `mvp_compliance/management.py` `create_declared_documents()` per plan.md steps 1, 2 and 5; connected in `MvpComplianceConfig.ready()`. `tests/test_app.py` gains the test that after `call_command("migrate", verbosity=0)` with a declaration set the document exists, which proves the connection (scenario 8, FR-010) | T001 and that test pass |
| T003 | `tests/test_management.py::TestRefusedDeclarations` — a declared name that belongs to a document under another slug raises `ImproperlyConfigured` whose message contains both slugs, and no document was created for another, valid declaration in the same call (scenario 9, FR-008); a slug with a capital, a slug of `agree`, an empty name and a name with a trailing space each raise `ImproperlyConfigured` naming the declaration's slug, and create nothing (scenario 10); two declarations giving the same name raise and create nothing; a declaration whose name is already its own document's is not a fault (edge case) | Fails before T004 |
| T004 | `create_declared_documents()` step 3 and 4 per plan.md, messages translatable, `en` catalog regenerated | T003 passes |
| T005 | Documentation for US-1: `docs/models.md` *Declaring documents*; `docs/pages.md` linking example; `README.md` setting entry; `CONTEXT.md` *Declared document*; `CHANGELOG.md` *Added*. `demo/settings.py` declares the privacy policy, the terms of use and the impressum, and `seed_demo` sets the kind of a document it is about to seed, after its early return for one that already has versions. The docs say a refused declaration leaves the migrations applied and that `migrate` run again after fixing the settings completes what was skipped (FR-015, FR-016) | Docs check green; `uv run python manage.py migrate` then `seed_demo` on an empty demo database leaves the impressum a notice with its versions |

## US-2 — Writing a document the site already links to (P2, issue #115)

| Id | Task | Done when |
|---|---|---|
| T006 | `tests/test_models.py::TestDeclaredSlug` — with a document declared and no version, `save()` with a new slug raises `DeclaredDocumentError` and the stored slug is unchanged; so do `Document.objects.filter(...).update(slug=...)` and `bulk_update(..., ["slug"])` (scenario 2, FR-011); name, kind and enforced still change through `save()` and `update()` (FR-012); with the declaration removed, the slug changes again while no version is published (scenario 4, FR-013); a declared document made a notice before its first version is published is outstanding for nobody after publication (scenario 3). `tests/test_exceptions.py` covers the new exception as it covers the others. `tests/test_admin.py::TestDeclaredDocumentAdmin` — the change form of a declared document with no version renders no `slug` input and its POST cannot change the slug, while name, kind and enforced change; an undeclared document with no version still has the input (scenario 1) | Fails before T007 |
| T007 | `DeclaredDocumentError`; the lock in `Document.save()` and `DocumentQuerySet.update()`; `DocumentAdmin.get_readonly_fields()` per plan.md. `docs/models.md` *When the slug is fixed*, naming the routes that refuse, and `CONTEXT.md` *Slug* updated; ADR 0019's Decision reads as the current rule, with the declared case; `CHANGELOG.md` entry extended. `en` catalog regenerated (FR-014 to FR-016) | T006 passes; full suite green |
