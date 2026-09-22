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

## 2026-09-22T11:54:00Z · Implementer US1 · T010/T011

Did: wrote `tests/test_widgets.py::TestMarkdownEditorWidget`, asserting the rendered widget
carries a marker attribute, a `data-toolbar` of exactly the seven declared controls in order, and
none of the forbidden ones (image, embed, table, tag, raw HTML).
Verified: `poetry run pytest tests/test_widgets.py` failed on collection —
`ModuleNotFoundError: No module named 'mvp_compliance.widgets'` — the right reason, since the
widget did not exist yet.
Next: T012, the widget itself.
Watch: nothing.

## 2026-09-22T11:55:00Z · Implementer US1 · T012

Did: added `mvp_compliance/widgets.py` — `MarkdownEditorWidget(forms.Textarea)` with `TOOLBAR`
(seven `(name, gettext_lazy label)` pairs), a marker attribute and the serialised toolbar on
`data-toolbar`, and a `Media` naming the two vendored EasyMDE files before the package's own
`markdown-editor.css`/`.js`.
Verified: `poetry run pytest tests/test_widgets.py` — 5 passed. `poetry run ruff check` and
`poetry run ruff format --check` on the two new files — clean. `poetry run mypy
mvp_compliance/widgets.py` — no issues.
Next: T013/T014, the JS and CSS that make the toolbar work in the browser.
Watch: nothing.

## 2026-09-22T11:58:00Z · Implementer US1 · T013

Did: added `markdown-editor.js`. Reads `data-toolbar` off each marked textarea, maps each declared
control to EasyMDE's own built-in action, and instantiates EasyMDE with `spellChecker: false`,
`status: false`, and no preview/side-by-side/full-screen control in the toolbar it builds.
Verified: `poetry run pytest tests/test_widgets.py` — 8 passed (the two new static-asset guard
tests exercise the file's content: every declared control appears, and none of the three
preview-family EasyMDE actions do). No JavaScript runtime exists in this suite, so the file's
actual behaviour in a browser is not something a test here can prove — see the report's `concerns`.
Next: T014.
Watch: browser behaviour unverified by test; observe on the demo server once T017 gives the
widget a page to render on, and say so as observation, not proof.

## 2026-09-22T11:59:00Z · Implementer US1 · T014

Did: added `markdown-editor.css` — one inline-SVG background per toolbar button class, sized to
16px, and a rule keeping the editor's container inside the admin's `field-markdown` box.
Verified: `poetry run pytest tests/test_widgets.py` — 8 passed, including the guard asserting
every declared toolbar control has a matching `.mvp-compliance-toolbar-<name>` rule.
`poetry run ruff check`/`ruff format --check` clean; pre-commit's whitespace/format hooks ran over
both new static files (D8 only excludes the vendored ones) and made one formatting fix, re-verified
green afterwards.
Next: T015/T016, the form.
Watch: same as T013 — icon rendering itself is a demo-server observation, not a test result.

## 2026-09-22T12:03:00Z · Implementer US1 · T015/T016

Did: wrote `tests/test_forms.py::TestVersionForm` (widget used, field names exactly `document` and
`markdown`, hand-typed Markdown round-trips unchanged), then `mvp_compliance/forms.py` —
`VersionForm(forms.ModelForm)` with `Meta.fields = ["document", "markdown"]` as an explicit allow
list and `markdown` on `MarkdownEditorWidget`.
Verified: red first — `ModuleNotFoundError: No module named 'mvp_compliance.forms'` on all three.
Green after: `poetry run pytest tests/test_forms.py` — 3 passed. One test fix along the way: the
round-trip sample's trailing newline was stripped by `CharField`'s default `strip=True`, which is
ordinary Django behaviour and not a reformatting the requirement is about, so the sample lost its
trailing newline rather than the assertion being weakened. `ruff check`/`ruff format --check` clean
on both files; `mypy mvp_compliance/forms.py` clean.
Next: T017, the admin.
Watch: nothing.

## 2026-09-22T12:06:00Z · Implementer US1 · T017

Did: wrote `tests/test_admin.py::TestVersionAdmin` against a self-contained `urlpatterns`
(`@pytest.mark.urls(__name__)`) mounting the admin for this module only — `tests/urls.py` is
outside this story's scope. Then `mvp_compliance/admin.py` — `DocumentAdmin` and `VersionAdmin`,
the latter with `form = VersionForm`, `readonly_fields` covering `number`/`status`/`published_at`/
`html`, and list display of document/number/status/published time.
Verified: red first — `NoReverseMatch` for all three admin URL names, since nothing was
registered. Green after: `poetry run pytest tests/test_admin.py` — 3 passed, reaching the add page
and a draft's change page as `editor` and finding the editor markup in both, and reading the
changelist's document/number/status columns. `ruff check`/`ruff format --check` clean;
`mypy mvp_compliance/admin.py` clean.
Next: T005 — narrow the two FS-001 assertions this admin now contradicts.
Watch: nothing.

## 2026-09-22T12:07:00Z · Implementer US1 · T005

Did: narrowed `tests/test_app.py`'s two FS-001 assertions per D11 (already recorded at plan time).
`test_it_ships_no_admin_forms_views_or_urls` -> `test_it_registers_no_public_urls`, keeping only
the half still true: `mvp_compliance.urls` does not exist (FR-008). `test_it_registers_nothing_in_
the_admin` -> `test_it_registers_both_models_in_the_admin`, its opposite. Both carry a comment
naming FS-002 as what superseded FS-001's D5.
Verified: confirmed both assertions failed by design before the edit (admin.admin now exists and
both models are registered) — the right reason. `poetry run pytest tests/test_app.py` — 4 passed
after narrowing. `ruff check`/`ruff format --check` clean.
Next: T018, the toolbar/allow-list agreement test.
Watch: this is the one pre-existing test this story is authorised to change, and only this far.

## 2026-09-22T14:00:00Z · Implementer US1 · demo-server observation

Did: signed into the running demo server as `editor.user` and requested the version add page, per
the brief's instruction to check the result there.
Watch: the page 404s. The demo server's worker process started at 13:44:21, before
`mvp_compliance/widgets.py` (13:53), `forms.py` (13:56) and `admin.py` (13:57) existed on disk —
Django's `StatReloader` only watches modules already imported at process start, so brand-new files
never trigger a restart the way an edit to an existing one does. This is an observation about the
demo server's process lifecycle, not a claim about the code: `tests/test_admin.py` reaches the same
add page through a fresh process per test run and finds the editor markup there. The brief says not
to start or stop the server, so this is left for Forge rather than restarted here.

## 2026-09-22T14:05:00Z · Implementer US1 · T018

Did: `tests/test_admin.py::TestToolbarAgreesWithTheAllowList` — one Markdown sample per declared
toolbar control against `MarkdownRenderer`, asserted to keep its element, plus a sample the allow
list strips, asserted to be stripped.
Verified: this test needed no new production code, so red/green was checked by mutation instead —
temporarily dropped `"a"` from `MarkdownRenderer.allowed_tags`, confirmed
`test_every_toolbar_control_survives_publication` failed on the `link` case with the stripped
output shown in the message, then restored the file (`git status --short mvp_compliance/rendering.py`
confirmed clean) and reran: `poetry run pytest tests/test_admin.py` — 5 passed.
`ruff check`/`ruff format --check` clean.
Next: T019, documentation.
Watch: nothing.

## 2026-09-22T14:10:00Z · Implementer US1 · T019

Did: README's status line updated (admin now exists) and a new "Writing a version" section
documents the toolbar and the vendoring choice. CHANGELOG gains an Added entry for the admin
registration and the widget. CONTEXT.md gains the **Compliance editor** glossary entry.
Verified: `poetry run pre-commit run --files README.md CHANGELOG.md CONTEXT.md` — clean
(whitespace/EOF hooks; no lint step applies to prose). Read back against the spec's own wording
for the role (US-1's framing, FS-002's context) for consistency.
Next: full story verify.
Watch: nothing.

## 2026-09-22T12:16:00Z · Implementer US2 · T020

Did: `tests/test_admin.py::TestDraftPrivacy` walks every address this feature serves that exists
yet — version changelist, add, change; document changelist, change — against anonymous, a
signed-in non-staff visitor, and staff holding no `mvp_compliance` permissions. All three reach
nothing (302 for the first two, 403 for the third) and none of a draft's wording appears in any
response. Preview and publish don't exist yet (US-3, US-4), so they are not covered; said so
rather than working around it.
Verified: this needed no production change — Django's own admin permission checks already refuse
all three callers — so red/green was checked by mutation instead. Temporarily added
`VersionAdmin.has_view_permission` returning `True` unconditionally: `poetry run pytest
tests/test_admin.py::TestDraftPrivacy::test_staff_without_permissions_reaches_nothing` then failed
on 2 of 5 addresses (`assert 200 == 403`, the version changelist and change pages). Reverted
(`git checkout -- mvp_compliance/admin.py`, confirmed clean with `git status --short`) and reran:
`poetry run pytest tests/test_admin.py::TestDraftPrivacy` — 15 passed. `ruff format` reformatted
the new block once; `ruff check` clean after.
Watch: the project's real 403 page (`mvp/403.html`, via the django-mvp shell) needs
`EASY_ICONS` configured to render — `tests/settings.py` doesn't carry it, and no test before this
one ever triggered a 403 to surface the gap. Worked around inside this module's own isolated
urlconf (`handler403`) rather than touching `tests/settings.py`, which is outside this story's
scope. Flagging in `concerns` for whoever owns that file next.
Next: T021, `has_delete_permission` on a published version.

## 2026-09-22T12:20:00Z · Implementer US2 · T021

Did: `VersionAdmin.has_delete_permission` returns `False` once a version has been published, so
the admin offers no delete link on its change page and refuses the delete view directly, matching
what `Version.delete()` already refuses at the model layer.
Verified: `poetry run pytest tests/test_admin.py::TestDraftPrivacy::test_a_published_version_offers_no_delete_action`
failed before the change — `assert b'.../delete/' not in <change page content>` — the delete link
was present and `GET` on the delete view returned 200. After the change: `poetry run pytest
tests/test_admin.py` — 21 passed. `ruff check`/`ruff format --check` clean on both files, `mypy
mvp_compliance/admin.py` — no issues.
Next: T022, a draft surviving being left alone.

## 2026-09-22T12:24:00Z · Implementer US2 · T022

Did: `TestDraftPrivacy::test_a_draft_survives_being_left_alone` — a draft fetched through the
change page and saved again through it keeps its wording and stays a draft.
Verified: needed no production change (Django's own `ModelForm` round trip already does this), so
checked by mutation. First mutation (`VersionForm.Meta.fields = ["document"]`, dropping
`markdown`) passed for the wrong reason — a field missing from the form just leaves the stored
value alone, proving nothing. Reverted, then added `clean_markdown` returning the value with `"!"`
appended: `poetry run pytest tests/test_admin.py::TestDraftPrivacy::test_a_draft_survives_being_left_alone`
failed — `assert 'Wording 0!' == 'Wording 0'`. Reverted (`git checkout -- mvp_compliance/forms.py`,
confirmed clean) and reran: `poetry run pytest tests/test_admin.py` — 22 passed. `ruff
check`/`ruff format --check` clean.
Next: T023, discarding a draft leaves other versions alone.

## 2026-09-22T12:28:00Z · Implementer US2 · T023

Did: `TestDraftPrivacy::test_discarding_a_draft_leaves_other_versions_alone` — a document with a
published version and a draft, deleting the draft through the admin removes only that row and
leaves the published one `CURRENT`.
Verified: needed no production change (an ordinary single-object admin delete), so checked by
mutation. Temporarily made `has_delete_permission` return `False` unconditionally:
`poetry run pytest tests/test_admin.py::TestDraftPrivacy::test_discarding_a_draft_leaves_other_versions_alone`
failed — `assert 403 == 302`, delete refused and the row still present. Reverted
(`git checkout -- mvp_compliance/admin.py`, confirmed clean) and reran: `poetry run pytest
tests/test_admin.py` — 23 passed. `ruff check`/`ruff format --check` clean.
Next: T024, several drafts of one document all listed and separately editable.

## 2026-09-22T12:32:00Z · Implementer US2 · T024

Did: `TestDraftPrivacy::test_every_draft_of_a_document_is_listed_and_separately_editable` — three
drafts of one document all appear on the version changelist, and each change page carries that
version's own wording and none of the other two's.
Verified: needed no production change (the admin's own default changelist and change views), so
checked by mutation. Temporarily added `get_queryset` excluding `status="draft"` to `VersionAdmin`:
`poetry run pytest tests/test_admin.py::TestDraftPrivacy::test_every_draft_of_a_document_is_listed_and_separately_editable`
failed — the change pages 404'd through to a redirect (`assert 302 == 200`), the drafts no longer
resolving through the admin's own queryset. Reverted (`git checkout -- mvp_compliance/admin.py`,
confirmed clean) and reran: `poetry run pytest tests/test_admin.py` — 24 passed. `ruff
check`/`ruff format --check` clean.
Next: T025, the packaged app's existing URL-surface assertion, exercised rather than rewritten.

## 2026-09-22T12:35:00Z · Implementer US2 · T025

Did: no new test — `tests/test_app.py::TestPackagedApp::test_it_registers_no_public_urls` is
T005's narrowed assertion, and it already exercises this task's given/when/then: a document whose
only version is a draft is invisible to a visitor because the package registers no public urls
module at all (FR-008, US-2 scenario 4). Nothing to add.
Verified: `poetry run pytest tests/test_app.py::TestPackagedApp::test_it_registers_no_public_urls`
— passed. Probed it can fail: wrote a transient `mvp_compliance/urls.py` (`urlpatterns = []`), reran
— failed (`find_spec(...) is None` no longer true, module spec resolved). Deleted the file
(`git status --short` confirmed clean) and reran: `poetry run pytest tests/test_app.py` — 4 passed.
Next: T026, README permissions section and CHANGELOG line.

## 2026-09-22T12:38:00Z · Implementer US2 · T026

Did: README gains a "Permissions" section — what `view_version`/`change_version` mean for
reaching a version at all, `add_version`/`delete_version` for writing and discarding drafts, and
that deleting a published version is refused regardless of who asks. CHANGELOG gains the matching
Added entry.
Verified: `poetry run pre-commit run --files README.md CHANGELOG.md` — clean (whitespace/EOF
hooks; no lint step applies to prose). Read back against the permissions actually granted in
`tests/conftest.py`'s `editor`/`publisher` fixtures and `Version.Meta.permissions` for accuracy.
Next: full story verify.

## 2026-09-22T12:30:59Z · Implementer US3 · T030

Did: extended `DRAFT_PRIVACY_ADDRESSES` with the preview URL, so the address-sweep tests already
proving draft privacy for every other address (`test_anonymous_reaches_nothing`,
`test_a_signed_in_non_staff_visitor_reaches_nothing`, `test_staff_without_permissions_reaches_nothing`)
parametrize over it too. Added `TestPreview::test_editor_receives_the_rendering_of_the_drafts_markdown`
— an editor's preview of a draft shows the HTML `get_renderer()` produces for its Markdown.
Verified: `poetry run pytest tests/test_admin.py::TestPreview tests/test_admin.py::TestDraftPrivacy`
— 4 failed, 19 passed, all four failures `NoReverseMatch` for `mvp_compliance_version_preview`,
the right reason (the URL does not exist yet). `poetry run pre-commit run --files
tests/test_admin.py` — clean.
Next: T031, the preview URL and view.

## 2026-09-22T12:34:00Z · Implementer US3 · T031

Did: `VersionAdmin.get_urls()` adds `<pk>/preview/`, wrapped in `admin_site.admin_view` and
checking `has_view_permission(request, obj)`. `preview_view` renders a draft through
`get_renderer()`, and reads the stored `html` field for a published version rather than
rendering it again (Article XIII). Added
`TestPreview::test_a_published_versions_preview_reads_the_stored_html_not_a_fresh_rendering` —
publishes a version, changes `MVP_COMPLIANCE_RENDERER` with `override_settings`, and asserts the
preview still shows the stored output rather than the new renderer's. A bare-bones
`preview.html` shows the rendered output inside a marked container; its heading and link back to
the version are T032's.
Verified: `poetry run pytest tests/test_admin.py` — 29 passed, including
`TestDraftPrivacy::test_staff_without_permissions_reaches_nothing[version preview]` returning 403
and the anonymous/visitor cases redirecting. `poetry run pre-commit run --files
mvp_compliance/admin.py mvp_compliance/templates/admin/mvp_compliance/version/preview.html
tests/test_admin.py` — clean (ruff, mypy, deptry).
Next: T032, the preview page's own heading and link back to the version.

## 2026-09-22T12:40:00Z · Implementer US3 · T032

Did: the preview template gains an `<h1>` stating this is what a reader will be served (US-3
scenario 5) and a link back to the version's change page, both translated.
Verified: `poetry run pytest tests/test_admin.py::TestPreview::test_the_preview_page_states_what_a_reader_will_be_served
tests/test_admin.py::TestPreview::test_the_preview_links_back_to_the_version` — both failed before
the template change (neither string was in the response), passed after. `poetry run pytest
tests/test_admin.py` — 31 passed. `poetry run pre-commit run --files
mvp_compliance/templates/admin/mvp_compliance/version/preview.html tests/test_admin.py` — clean
(one ruff-format line-wrap applied and reverified).
Next: T033, previewed content the allow list strips shows as stripped.

## 2026-09-22T12:44:00Z · Implementer US3 · T033

Did: `TestPreview::test_the_preview_shows_stripped_content_as_stripped` — a draft holding a
`<script>` tag previews with it removed, using a distinctive marker string so the assertion
cannot be satisfied by the admin chrome's own legitimate `<script src=...>` tags.
Verified: needed no production change — T031's `preview_view` already calls `get_renderer()` for
a draft, which sanitises. `poetry run pytest
tests/test_admin.py::TestPreview::test_the_preview_shows_stripped_content_as_stripped` passed
first run. Probed it can fail: temporarily had `preview_view` read `version.markdown` directly
instead of `get_renderer()().render(...)` — failed (`mvp-compliance-preview-test` string appeared
unstripped in the response). Reverted (`git checkout -- mvp_compliance/admin.py`, confirmed
clean) and reran: `poetry run pytest tests/test_admin.py` — 32 passed. `poetry run pre-commit run
--files tests/test_admin.py` — clean.
Next: T034, what was previewed is what publication stores (SC-004).

## 2026-09-22T12:48:00Z · Implementer US3 · T034

Did: `TestPreview::test_what_was_previewed_is_what_publication_stores` — previews a draft,
extracts the rendered content from the response with a regex over the marked container, publishes
the draft, and asserts `Version.html` is identical to what the preview showed.
Verified: needed no production change — D10's design already makes this true by construction.
`poetry run pytest tests/test_admin.py::TestPreview::test_what_was_previewed_is_what_publication_stores`
passed first run. Probed it can fail: temporarily had `Version.publish()` append `<p>tampered</p>`
to its rendered html — failed (`assert '<p>Wording 0</p><p>tampered</p>' ==
'<p>Wording 0</p>'`). Reverted (`git checkout -- mvp_compliance/models.py`, confirmed clean) and
reran: `poetry run pytest tests/test_admin.py` — 33 passed. `poetry run pre-commit run --files
tests/test_admin.py` — clean.
Next: T035, a Preview control on the change form.

## 2026-09-22T12:52:00Z · Implementer US3 · T035

Did: `mvp_compliance/templates/admin/mvp_compliance/version/change_form.html` overrides
`object-tools-items` to add a Preview link (only on the change page, not add), leaving the
default History/View-on-site tools via `{{ block.super }}`. Added
`TestPreview::test_the_change_form_offers_the_preview`.
Verified: `poetry run pytest tests/test_admin.py::TestPreview::test_the_change_form_offers_the_preview`
— failed before the template (`preview_url` absent from the change page), passed after. `poetry
run pytest tests/test_admin.py` — 34 passed. `poetry run pre-commit run --files
mvp_compliance/templates/admin/mvp_compliance/version/change_form.html tests/test_admin.py` —
clean (one ruff-format line-wrap applied and reverified).
Next: T036, README and CHANGELOG.

## 2026-09-22T12:56:00Z · Implementer US3 · T036

Did: README's status line now says previewing is built, and gains a "Previewing a version"
section: the `<version>/preview/` address, what distinguishes it from the toolbar's inline
display (a fresh rendering for a draft, the stored html for a published version, never rendered
again), and the `view_version` permission it needs. CHANGELOG gains the matching Added entry.
Verified: `poetry run pre-commit run --files README.md CHANGELOG.md` — clean (no lint step
applies to prose; whitespace/EOF hooks passed). Read back against `mvp_compliance/admin.py`'s
actual url name and permission check, and `mvp_compliance/templates/.../preview.html`'s actual
heading, for accuracy.
Next: full story verify.

## 2026-09-22T15:15:00Z · Implementer US5 · T050

Did: `TestDocumentAdmin::test_starting_the_next_version_opens_with_the_current_wording` — a
document with a published version, requesting the version add page with `?document=<pk>`, asserts
the current version's markdown appears in the response.
Verified: `poetry run pytest tests/test_admin.py::TestDocumentAdmin -x` — failed first run (200 OK,
markdown absent from the box), the right reason for a page that does not read the query string yet.
Next: T051, `VersionAdmin.get_changeform_initial_data()`.

## 2026-09-22T15:17:00Z · Implementer US5 · T051

Did: `VersionAdmin.get_changeform_initial_data()` calls `super()` for Django's own query-string
initial data, then, when a `document` id came through, reads `Document.current` (the property
US-1's foundational work already carries and nothing had consumed yet) and adds its `markdown` to
initial when a version is in force.
Verified: `poetry run pytest tests/test_admin.py::TestDocumentAdmin` — T050's test passed.
`poetry run pytest tests/test_admin.py::TestVersionAdmin tests/test_admin.py::TestPublish
tests/test_admin.py::TestDraftPrivacy` — 37 passed, no regression. `poetry run ruff check
mvp_compliance/admin.py tests/test_admin.py` and `poetry run mypy mvp_compliance/admin.py` — clean.
Next: T052, the empty-box case.

## 2026-09-22T15:19:00Z · Implementer US5 · T052

Did: `TestDocumentAdmin::test_a_document_with_nothing_in_force_opens_empty` — a document holding
only a draft (never published) opens the add page with that draft's markdown absent from the box,
so a version that is not in force never leaks into the initial value.
Verified: `poetry run pytest tests/test_admin.py::TestDocumentAdmin` — passed on the first run, as
T051's design already covers it (no production change needed, matching the task's own "Done when:
Passes"). `poetry run ruff check tests/test_admin.py` — clean.
Next: T053, the link on the document's change form.

## 2026-09-22T15:22:00Z · Implementer US5 · T053

Did: `TestDocumentAdmin::test_the_document_page_offers_the_next_version` first, asserting the
document's change page carries a link to `.../version/add/?document=<pk>`. Then
`mvp_compliance/templates/admin/mvp_compliance/document/change_form.html`, mirroring the version
template's `object-tools-items` override T035 used for Preview: a **Start the next version** link,
guarded by `{% if change %}` so the add page (no `original`) never tries to render it, wrapped in
`{% translate %}`.
Verified: the test failed before the template (200 OK, link absent), passed after. `poetry run
pytest tests/test_admin.py::TestDocumentAdmin tests/test_admin.py::TestDraftPrivacy
tests/test_admin.py::TestVersionAdmin` — 28 passed. `poetry run djlint
mvp_compliance/templates/admin/mvp_compliance/document/change_form.html --check` — one line-wrap
needed on the long `href`/`class` pair, applied and reverified clean. `poetry run pre-commit run
--files` on the template — clean.
Next: T054, the copy leaves the source alone.

## 2026-09-22T15:25:00Z · Implementer US5 · T054

Did: `TestDocumentAdmin::test_editing_the_copy_leaves_the_published_version_alone` — publishes a
version, starts a new one from the same document's add page, posts it with different wording, then
re-reads the published version and asserts its markdown and html are exactly what they were before
the post.
Verified: needed no production change — the add view always creates a new row, and
`Version.save()`'s existing frozen-field guard (Article XII, already in place before this story)
would refuse a write to the published row even if something tried to reach it. `poetry run pytest
tests/test_admin.py::TestDocumentAdmin` — passed first run. `poetry run ruff check
tests/test_admin.py` — clean.
Next: T055, README and docs/authoring.md.

## 2026-09-22T15:30:00Z · Implementer US5 · T055

Did: README gains a "Starting the next version from the one in force" section between Publishing
and Scope & philosophy. `docs/authoring.md` gains the matching section between Publishing and Who
can do what, naming `get_changeform_initial_data()` and the property it reads. CHANGELOG gains the
Added entry.
Verified: `poetry run pre-commit run --files README.md CHANGELOG.md docs/authoring.md` — clean.
`/home/sam/.openclaw/workspaces/forge/engineering-org/kit/forge verify --repo . --base origin/main
--step docs` — passed. Read back against `mvp_compliance/admin.py`'s actual method name and
`DocumentAdmin`'s actual template for accuracy.
Next: T056, makemessages.

## 2026-09-22T15:35:00Z · Implementer US5 · T056

Did: `DJANGO_SETTINGS_MODULE=tests.settings poetry run python manage.py makemessages -l en` from
the repository root. Picked up "Start the next version" — first run marked it `#, fuzzy` against
the similarly-worded existing "Back to this version" and copied that msgstr; corrected the msgstr
to match its own msgid and dropped the fuzzy markers by hand, the way an editor resolving a fuzzy
match would. Also stripped the `POT-Creation-Date` line both times it reappeared, matching the
existing house convention (this feature's own prior commit, "Keep the message catalog's file
references relative to the repository") of keeping that line out because it changes on every run
and makes the file diff for a reason unrelated to any string in it.
Verified: `poetry run pytest tests/test_admin.py::TestUserFacingStrings` — both tests passed
against the regenerated catalog. Ran `makemessages` a second time against the committed file: the
only line it wanted to add back was `POT-Creation-Date`, which was removed again, leaving `git
diff` empty — the catalog is stable across repeated runs, T056's "Done when". Full story verify:
`/home/sam/.openclaw/workspaces/forge/engineering-org/kit/forge verify --repo . --base
origin/main` — conformance, docs, poetry:lint, poetry:typecheck, poetry:test (131 passed),
poetry:build all passed. `git status --short` — clean.

## 2026-09-22 — S5 CONVERGE

All five stories accepted after independent re-verification. One branch-local migration, so nothing
to consolidate. Migrate-from-zero reaches the same state and `makemigrations --check` is clean.

The cleanup pass found one real inconsistency rather than only noise. The preview branched
carefully between rendering a draft and reading a published version's stored output; the publish
confirmation did not, and rendered whatever it was given. Nothing was ever written either way, so
no stored evidence was at risk and the suite was green — but a published version's confirmation
page is reachable, and it was showing a fresh rendering of wording somebody had already been served
a different rendering of. Both pages now ask one method. The test reinstates the defect: with the
branch removed, the preview's assertion and the new one both go red.

Folding the two views into that method also removed their duplicated page setup, so the only
difference left between them is the one that matters.

The catalog convention two implementers rediscovered the hard way is now a comment in the catalog's
own header, which is the file somebody about to regenerate it has open.

One decision graduated to an architecture record: vendoring the editor rather than depending on it
or fetching it (ADR 0007). The other fifteen stay where they are, each with its reason.
