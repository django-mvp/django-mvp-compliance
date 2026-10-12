
## 2026-10-12T10:33:18Z · Orchestrator · plan

Research, plan and tasks written against main at 72fb4c0, which carries FS-009 as delivered. The FS-010 spec was read against FS-009's and nothing contradicts: the three amendments it makes to FS-009 are the ones FS-009's own decisions D16 and D22 left for it. Stories are built in dependency order: US-2, US-1, US-3, then US-4 to US-6 together (decisions.md D17). Next: design review.

## 2026-10-12T10:50:34Z · Implementer US2 · T002

Did: wrote TestEnforcement (tests/test_models.py) and TestEnforcedColumn (tests/test_migrations.py), tests first. Both classes are red on purpose until T003.
Verified: uv run pytest tests/test_models.py::TestEnforcement -q -> 11 failed (no `enforced` field, no enforced_outstanding_for); uv run pytest tests/test_migrations.py::TestEnforcedColumn -q -> 1 failed at the assertion that the document is enforced; pre-commit on both files passes.
Next: T003, the field, queryset method, migration 0002, docs/models.md and catalog.
Watch: the add/remove of the field changes what makemigrations --check sees, so T003 must carry the migration in the same commit. The brief file lacks a trailing newline, so pre-commit --all-files rewrites it; left alone as out of scope.

## 2026-10-12T10:52:39Z · Implementer US2 · T003

Did: Document.enforced (BooleanField, default True, with verbose_name and help_text), DocumentQuerySet.enforced_outstanding_for() and the forwarding DocumentManager method, migration 0002_document_enforced (one AddField, no RunPython), docs/models.md (a section on enforcement and one on enforced_outstanding_for() beside Outstanding), and the en catalog regenerated. makemessages marked the new "enforced" entry fuzzy with the translation "In force"; set it to the string itself and gave the help text its identical msgstr, like its neighbours.
Verified: uv run pytest tests/test_models.py::TestEnforcement tests/test_models.py::TestModelFields tests/test_migrations.py -q -> 37 passed. Mutation probe: dropping .filter(enforced=True) made test_leaves_out_a_document_that_is_not_enforced fail. makemigrations --check --dry-run -> No changes detected. makemessages run a second time leaves the catalog unchanged apart from its creation date.
Next: T004, the admin tests.
Watch: BLOCKED ON ONE PRE-EXISTING TEST. tests/test_models.py::TestDocument::test_document_holds_no_wording asserts the concrete fields of Document are exactly {id, name, slug, kind}, so it fails for any new field. It is not mine to change; the one-line edit it needs is to add "enforced" to that set. Everything else in tests/test_models.py and tests/test_migrations.py passes.
