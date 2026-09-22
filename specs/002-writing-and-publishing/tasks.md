# Tasks — 002 Writing and publishing a document without a developer

Derived from [plan.md](./plan.md). Task ids are stable and are what `feature-state.json` tracks.
Every task follows Article I: the failing test comes first.

Every admin page is exercised through the `client` fixture against a real user holding a real
permission set. A test that calls a `ModelAdmin` method directly proves nothing about what a
request receives, and the permission requirements here are all about what a request receives.

**The five stories are sequentially dependent and must not be dispatched in parallel.** US-1
creates `mvp_compliance/admin.py`, and every story after it adds methods to the two classes that
file defines. Two of them in separate worktrees would each write their own version of it and
collide at convergence, and any of them starting before US-1 has committed would have no file to
add to.

## Foundational — sequential, before any story

| Id | Task | Done when |
|---|---|---|
| T001 | Vendor EasyMDE 2.21.0 into `mvp_compliance/static/mvp_compliance/vendor/easymde/`: `easymde.min.js` and `easymde.min.css` unmodified from the published tarball, the upstream `LICENSE`, and `VERSION.md` recording the version, the source URL and the SHA-256 of each file | Both files present, hashes in `VERSION.md` match `sha256sum` output, `MANIFEST`/`pyproject` packaging includes them in the built wheel |
| T002 | `tests/factories.py` — `UserFactory` (one per model, `factory.Sequence` on the email/username, no variant subclasses). `tests/test_factories.py` extended to cover it | Passes; Article X's one-factory-per-model rule holds |
| T003 | `tests/conftest.py` — fixtures for the callers every story tests against: `editor` (staff, `view`/`add`/`change`/`delete` on `Version` and `Document`), `publisher` (staff, those plus `publish_version`), `staff_without_permissions`, `visitor` (signed in, not staff). Each a thin wrapper over `UserFactory` with permissions set at the call site | Used by the modules below rather than per-test construction |
| T004 | `mvp_compliance/models.py` — `Version.Meta.permissions` gains `("publish_version", _("Can publish a version"))`, and `makemigrations mvp_compliance` writes `0002`. A test asserts the permission exists in the database after migration | `makemigrations --check` clean; migrate-from-zero reaches the same state |
| T006 | `demo/` — mount `django.contrib.admin` in `demo/urls.py`, add `demo/management/commands/seed_demo.py` seeding the three fleet-standard accounts (`regular.user@`, `staff.user@`, `super.user@example.com`, password `password`) plus an `editor.user@` and a `publisher.user@` holding exactly the permission sets US-2 and US-4 turn on, and a document in every state: no versions, one draft only, one published, and one published plus a superseded predecessor. `demo/templates/demo/landing.html` points at the admin and lists the accounts | `python manage.py seed_demo` is idempotent and the demo server serves every state without anybody creating a row by hand |

## US-1 — Write a version without knowing Markdown (P1, issue #14)

| Id | Task | Done when |
|---|---|---|
| T010 | `tests/test_widgets.py::TestMarkdownEditorWidget` — the widget renders a `textarea` carrying the marker attribute and a `data-toolbar` whose entries are exactly heading, bold, italic, unordered list, ordered list, link and quote (FR-002) | Fails before T012 |
| T011 | `tests/test_widgets.py::TestMarkdownEditorWidget::test_it_offers_no_forbidden_control` — the rendered `data-toolbar` contains no image, embed, table, tag or raw-HTML entry, asserted against the served markup rather than a Python attribute (FR-003, US-1 scenario 2) | Fails before T012 |
| T012 | `mvp_compliance/widgets.py` — `MarkdownEditorWidget(forms.Textarea)` with `TOOLBAR`, the marker attribute, the serialised toolbar in `data-toolbar`, and a `Media` naming the two vendored files then `markdown-editor.css` and `markdown-editor.js`. Every label on a toolbar entry wrapped with `gettext_lazy` | T010 and T011 pass |
| T013 | `mvp_compliance/static/mvp_compliance/markdown-editor.js` — reads `data-toolbar` off each marked textarea and instantiates EasyMDE with it, `spellChecker: false`, `status: false`, and no preview, side-by-side or full-screen control (`research.md` R6) | The demo's add page renders a working toolbar with six groups and nothing else |
| T014 | `mvp_compliance/static/mvp_compliance/markdown-editor.css` — one inline-SVG icon per toolbar class, and the sizing that fits the control inside the admin's change form. No Font Awesome, no web font, no external URL (`research.md` R3) | Every button shows its icon on the demo server |
| T015 | `tests/test_forms.py::TestVersionForm` — the form's `markdown` field uses the widget, the value submitted is stored verbatim as Markdown, and Markdown typed by hand round-trips unchanged (FR-005, US-1 scenario 3) | Fails before T016 |
| T016 | `mvp_compliance/forms.py` — `VersionForm(forms.ModelForm)` over `Version`, `markdown` on `MarkdownEditorWidget`, and `Meta.fields = ["document", "markdown"]` as an explicit allow list. `tests/test_forms.py::TestVersionForm::test_it_exposes_only_what_an_author_supplies` asserts the form's field names are exactly those two, so `html` — evidence produced by `publish()` under Article XIII — is never postable | T015 passes and the new assertion passes |
| T017 | `mvp_compliance/admin.py` — `VersionAdmin` registered with `form = VersionForm` and `readonly_fields` covering `number`, `status`, `published_at` and `html`, so a version's full state is readable without any of it being writable. `DocumentAdmin` registered. List display, search and ordering that make the changelist usable: document, number, status, published time | `tests/test_admin.py::TestVersionAdmin` reaches the add and change pages as `editor` and finds the editor markup in the response |
| T005 | `tests/test_app.py::test_it_ships_no_admin_forms_views_or_urls` narrowed to `test_it_registers_no_public_urls`: `mvp_compliance.urls` still does not exist, and the package's only addresses are the admin's. `test_it_registers_nothing_in_the_admin` replaced by its opposite — `Document` and `Version` are both registered. Both changes carry a comment naming FS-002 as what superseded FS-001's D5, and `decisions.md` D11 records it. Lands here rather than in the foundational phase because both assertions need `admin.py` to exist, which T017 is what creates | `forge tamper-check` flags the change, and D11 is the triage record that clears it |
| T018 | `tests/test_admin.py::TestToolbarAgreesWithTheAllowList` — one Markdown sample per toolbar control, each rendered through `MarkdownRenderer`, each asserted to keep the element it produces; and one sample of content the allow list strips, asserted to be stripped, so the test fails in both directions (FR-004, SC-002, US-1 scenario 4) | Passes, and a control added to `TOOLBAR` without a matching sample fails it |
| T019 | README gains the authoring surface and the widget; CHANGELOG gains its Added entry; `CONTEXT.md` gains the **Compliance editor** entry the specification names. Humanized per the public-markdown checklist | `forge verify --base origin/main` docs step is green |

## US-2 — A draft belongs to its author until it is published (P1, issue #15)

| Id | Task | Done when |
|---|---|---|
| T020 | `tests/test_admin.py::TestDraftPrivacy` — every address this feature serves (version changelist, add, change, preview, publish; document changelist and change) requested by `visitor`, `staff_without_permissions` and anonymous, each asserted to reach nothing and to leak no part of the draft's wording into the response (FR-007, SC-003, US-2 scenario 3) | Fails before T021 for the addresses that do not exist yet, passes for the rest |
| T021 | `mvp_compliance/admin.py` — `VersionAdmin.has_view_permission`/`has_change_permission`/`has_add_permission`/`has_delete_permission` left to Django's model permissions, with `has_delete_permission` returning `False` for a published object so the admin never offers an action `Version.delete()` would refuse | T020 passes |
| T022 | `tests/test_admin.py::TestDraftPrivacy::test_a_draft_survives_being_left_alone` — a draft saved, re-fetched and re-saved through the change form keeps its wording and stays a draft (US-2 scenario 1, FR-006) | Passes |
| T023 | `tests/test_admin.py::TestDraftPrivacy::test_discarding_a_draft_leaves_other_versions_alone` — deleting a draft through the admin removes it and leaves the document's other versions untouched (US-2 scenario 2) | Passes |
| T024 | `tests/test_admin.py::TestDraftPrivacy::test_every_draft_of_a_document_is_listed_and_separately_editable` — several drafts of one document all appear on the changelist and each opens its own editable form (US-2 scenario 5, FR-009) | Passes |
| T025 | `tests/test_app.py::TestPackagedApp::test_it_registers_no_public_urls` — the package's URL surface is the admin's and nothing else, so a document whose only version is a draft is invisible to a visitor (FR-008, US-2 scenario 4) | Passes; this is T005's narrowed assertion, exercised here |
| T026 | README's permissions section: what `view`/`change` on a version means and who needs it. CHANGELOG line | Docs step green |

## US-3 — Read it back the way the public will see it (P1, issue #16)

| Id | Task | Done when |
|---|---|---|
| T030 | `tests/test_admin.py::TestPreview` — `editor` requesting a draft's preview receives the rendering `get_renderer()` produces for its Markdown; `staff_without_permissions`, `visitor` and anonymous are refused (FR-010, FR-012, US-3 scenarios 1 and 4) | Fails before T031 |
| T031 | `mvp_compliance/admin.py` — `VersionAdmin.get_urls()` adds `<pk>/preview/` named `mvp_compliance_version_preview`, wrapped in `admin_site.admin_view` and checking `has_view_permission(request, obj)`. Renders a draft through `get_renderer()`; reads stored `html` for a published version, because Article XIII forbids re-rendering one | T030 passes |
| T032 | `mvp_compliance/templates/admin/mvp_compliance/version/preview.html` — extends the admin's base, states in its heading that this is the rendering a reader will be served, shows the output, and links back to the version. `{% load i18n %}` and every string translated | Renders on the demo server for a draft and for a published version |
| T033 | `tests/test_admin.py::TestPreview::test_the_preview_shows_stripped_content_as_stripped` — a draft holding content the allow list removes previews without it, so the loss is visible before publication rather than after (FR-011, US-3 scenario 3, US-1 scenario 5) | Passes |
| T034 | `tests/test_admin.py::TestPreview::test_what_was_previewed_is_what_publication_stores` — preview a draft, capture the rendering from the response, publish it, assert the stored `html` is identical (SC-004, US-3 scenario 2) | Passes |
| T035 | `mvp_compliance/templates/admin/mvp_compliance/version/change_form.html` — adds a **Preview** link to the change form's object tools, and the **Publish** link US-4 adds. The preview link is present for any version the caller may view | `tests/test_admin.py::TestPreview::test_the_change_form_offers_the_preview` passes |
| T036 | README gains the preview address and what distinguishes it from the editor's inline display. CHANGELOG line | Docs step green |

## US-4 — Publishing is deliberate, and there is no way back (P1, issue #17)

| Id | Task | Done when |
|---|---|---|
| T040 | `tests/test_admin.py::TestPublish` — `editor` (no `publish_version`) is refused at the publish address by both GET and POST and the version stays a draft; `publisher` reaches it (FR-014, US-4 scenario 1) | Fails before T041 |
| T041 | `mvp_compliance/admin.py` — `VersionAdmin.get_urls()` adds `<pk>/publish/` named `mvp_compliance_version_publish`, wrapped in `admin_site.admin_view`, refusing a caller without `mvp_compliance.publish_version` on both verbs | T040 passes |
| T042 | `tests/test_admin.py::TestPublish::test_a_get_confirms_and_publishes_nothing` — GET renders the confirmation, states that the wording cannot be changed afterwards and that a correction means another version, and leaves the version a draft (FR-015, US-4 scenario 2) | Fails before T043 |
| T043 | `mvp_compliance/templates/admin/mvp_compliance/version/publish_confirmation.html` — names the document and version, shows the rendering about to go live, states the consequence in plain words, offers one control that publishes and one that goes back. `{% load i18n %}`, every string translated, no claim of compliance | T042 passes |
| T044 | `tests/test_admin.py::TestPublish::test_a_post_publishes_and_declining_does_not` — POST makes the version current and supersedes whatever held it; following the back link instead leaves the draft untouched (FR-016, US-4 scenario 3) | Fails before T045 |
| T045 | `mvp_compliance/admin.py` — the publish view's POST branch calls `Version.publish()` inside a `try`, catching `PublishError` and adding the exception's own message with `messages.error` before redirecting to the change page (FR-018, US-4 scenarios 6 and 7). `PublishError` only: both refusals FR-018 names raise it, and the `save()` inside `publish()` runs while the stored row is still a draft, so `refuse_if_published_wording_changed` returns before it can raise `PublishedVersionError` — a second `except` branch there would be unreachable and untestable | T044 and T046 pass |
| T046 | `tests/test_admin.py::TestPublish::test_both_refusals_reach_the_author_as_a_message` — a version whose Markdown renders to nothing, and a version already published, each produce a readable message on the redirect rather than a traceback (FR-018, SC-007) | Passes |
| T047 | `tests/test_admin.py::TestPublish::test_saving_a_draft_publishes_nothing` — posting the change form with every field filled leaves the version a draft, and no admin action, field or checkbox anywhere offers publication (FR-013, US-4 scenario 4) | Passes |
| T048 | `tests/test_admin.py::TestPublish::test_a_published_version_has_no_editable_form` — the change page for a published version is served to `editor` with its wording readable, no input or textarea named `markdown`, and no save control; asserted against the served HTML (FR-017, SC-006, US-4 scenario 5) | Fails before T049 |
| T049 | `mvp_compliance/admin.py` — `VersionAdmin.has_change_permission(request, obj)` returns `False` for a published object, so Django serves its own read-only page (`research.md` R7) | T048 passes |
| T049a | `tests/test_admin.py::TestUserFacingStrings::test_nothing_claims_compliance` — sweep every user-facing string this feature ships, taken from the compiled catalog rather than a hand-kept list, and assert none of them says or implies that publishing makes a site compliant with anything (FR-019, SC-008, US-4 scenario 8) | Passes, and a new string is covered without anybody adding it to a list |
| T049b | `tests/test_admin.py::TestUserFacingStrings::test_every_string_is_translatable` — the `en` catalog holds every string the feature's Python and templates show a person (FR-020, SC-008) | Passes after `makemessages` |
| T049c | README gains the publish permission, the confirmation step and the read-only page. CHANGELOG line | Docs step green |

## US-5 — Start the next version from the one in force (P2, issue #18)

| Id | Task | Done when |
|---|---|---|
| T050 | `tests/test_admin.py::TestDocumentAdmin::test_starting_the_next_version_opens_with_the_current_wording` — with a document holding a version in force, the add page reached from that document opens with the current Markdown in the box (FR-021, US-5 scenario 1) | Fails before T051 |
| T051 | `mvp_compliance/admin.py` — `VersionAdmin.get_changeform_initial_data()` reads the document from the query string and returns the in-force version's `markdown` alongside it | T050 passes |
| T052 | `tests/test_admin.py::TestDocumentAdmin::test_a_document_with_nothing_in_force_opens_empty` — the ordinary case for a new document (US-5 scenario 3) | Passes |
| T053 | `mvp_compliance/templates/admin/mvp_compliance/document/change_form.html` — a **Start the next version** link in the document's object tools, pointing at the version add page for that document. Translated | `tests/test_admin.py::TestDocumentAdmin::test_the_document_page_offers_the_next_version` passes |
| T054 | `tests/test_admin.py::TestDocumentAdmin::test_editing_the_copy_leaves_the_published_version_alone` — save the new version with different wording, then assert the version it was copied from still holds its original Markdown and its original stored HTML (FR-022, US-5 scenario 2) | Passes |
| T055 | README gains the starting-point behaviour. CHANGELOG line | Docs step green |
| T056 | `makemessages` over the package, so `locale/en/LC_MESSAGES/django.po` holds every string this feature added | `makemessages` reports no change on a second run |
