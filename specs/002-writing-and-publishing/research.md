# Research — 002 Writing and publishing a document without a developer

What had to be settled before the plan could name a design. Each entry states the question, what
was checked, and the answer the plan relies on.

## R1 — The specification presupposes an editor that renders formatting as you type

US-3 scenario 5 compares "the editor's own inline formatting display" with the preview and rules
that they are two different things. That scenario is only meaningful against an editor that *has*
an inline display. A toolbar written over a plain `<textarea>` has none — the buttons would insert
Markdown characters and the author would look at the characters — so the scenario would be
untestable and the comparison it draws would have nothing on one side of it.

This narrows the field before any other consideration: the editor has to render its own markup
while it is being written. In practice that means a CodeMirror- or ProseMirror-based control.

## R2 — EasyMDE is the control, and it is currently maintained

[EasyMDE](https://github.com/Ionaru/easy-markdown-editor) is a CodeMirror 5 editor that styles
Markdown inline while it is typed, stores ordinary Markdown as the textarea's value, and takes its
toolbar as an explicit list rather than offering a fixed one.

Checked 2026-09-22 against the sources rather than a summary of them:

| Question | Answer | Where checked |
|---|---|---|
| Latest release | 2.21.0, published 2026-05-03 | npm registry metadata for `easymde` |
| Still worked on | Last push 2026-08-11, not archived | GitHub repository metadata |
| Licence | MIT | Repository metadata and the `LICENSE` file in the published tarball |
| Distribution size | `easymde.min.js` 327,475 bytes, `easymde.min.css` 12,923 bytes | Extracted from `easymde-2.21.0.tgz` |
| Toolbar restrictable | Yes — `toolbar` takes an array, and an unlisted button does not exist | Documented option, confirmed against `types/easymde.d.ts` |
| Stores plain Markdown | Yes — the control writes through to the original textarea | Documented behaviour |

The alternative worth naming is `django-markdownx`, which the FairDM project already runs. It is
rejected here on the requirements rather than on taste: it offers **no formatting toolbar at all**
(FR-002 is its whole purpose), and it ships drag-and-drop image upload, which FR-003 forbids. A
package whose headline feature is prohibited and whose required feature is absent is the wrong
starting point however familiar it is.

## R3 — EasyMDE ships no icons, and expects Font Awesome 4 class names

This is the trap in the previous entry, and it is not in the documentation's foreground. The
distributed stylesheet contains no icon rules at all (`grep -c 'fa-' easymde.min.css` → 0), while
the script writes `<i class="fa fa-bold">` and twenty sibling class names into the toolbar it
builds. Dropped into a Django admin page with only the two distributed files, every toolbar button
renders as an empty box.

The answer is not to add Font Awesome. A whole icon font for six buttons is a poor trade, and this
package has no other use for one.

Instead, each toolbar button is declared with its own `className`, and the package's own stylesheet
draws it from an inline SVG. Six icons, a few hundred bytes, no font, no network request, and the
button set becomes a single declaration in one file — which is what FR-003 needs to be checkable
in the first place.

## R4 — Vendored, not fetched

The two distributed files are committed to the repository under
`mvp_compliance/static/mvp_compliance/vendor/easymde/`, beside the upstream `LICENSE` and a short
note recording the version and the SHA-256 of each file.

A content delivery network was considered and rejected. Article XV says nothing this package holds
is transmitted off the host project's own infrastructure; a third-party asset tag reverses that for
every visitor to the page and hands a third party the ability to change what runs inside an
authenticated admin session. A Python wrapper package around the same two files was also
considered: it would add a runtime dependency, a release cadence and a second opinion about the
toolbar, in exchange for two files this package would still have to configure.

340 KB of vendored assets is the cost. It is stated in Complexity Tracking rather than passed over.

## R5 — The preview renders the stored row, not the editor's buffer

FR-010 requires a preview produced by the rendering the published page will use, and SC-004
requires that what publication stores is identical to what the preview showed.

Two designs satisfy the first. Only one satisfies the second.

Rendering the editor's unsaved buffer would show an author their current text, but publication
renders what is *stored*, so an author who previews, keeps typing and then publishes gets something
the preview never showed. Rendering the stored row makes SC-004 true by construction: the preview
and `publish()` read the same field through the same renderer, and there is no window in which they
can disagree.

The cost is that an author saves before previewing. That is one extra click on a path that already
ends in an irreversible act, and it is the same order Django's admin imposes everywhere else.

## R6 — EasyMDE's own preview button is turned off

EasyMDE ships a preview toggle that renders Markdown client-side with `marked`. That is a second
preview, produced by a different library, with none of this package's sanitising applied. It would
show an author content the allow list strips as if it had survived, which is precisely the failure
FR-011 exists to prevent.

The toolbar therefore omits it, along with the side-by-side and full-screen toggles that lead to
the same renderer. One preview, server-side, authoritative.

## R7 — Refusing to edit a published version is a permission answer, not a form answer

FR-017 wants a published version readable in full with no editable form, and the specification's
assumptions rule out "a form whose fields are disabled" and "a form whose save is refused".

Django already has this exact state. When `ModelAdmin.has_change_permission()` returns `False` for
an object and `has_view_permission()` returns `True`, the admin renders its read-only change form:
field values as text rather than inputs, and no submit row. Returning `False` per object is enough,
and the alternative — a bespoke template — would duplicate a page Django maintains.

The test asserts the served HTML, not the method's return value: no input or textarea named
`markdown`, and no `_save` control anywhere in the page.

## R8 — The permission to publish is a model permission, declared on `Version`

FR-014 wants publishing behind a permission separate from the one that allows writing drafts.
Django's four automatic permissions (`add`, `change`, `delete`, `view`) carry no fifth meaning, so
`Version.Meta.permissions` declares `publish_version`, which Django creates alongside them and
which appears in the ordinary permission list of the ordinary user admin.

This also gives the specification's odd-but-coherent case a natural expression: somebody holding
`publish_version` and not `change_version` can publish what exists and write nothing.

## R9 — Every address this feature serves belongs to the admin

`ModelAdmin.get_urls()` mounts the preview and the confirmation page underneath the admin's own
URL namespace, wrapped in `admin_site.admin_view`, which refuses anyone not signed in as staff
before the view runs at all.

Nothing here adds `mvp_compliance/urls.py`, so there is still no address a member of the public can
reach — which is FR-008 satisfied by there being no public surface yet rather than by a check. The
public pages are R2, and the test that FS-001 wrote to hold this line is narrowed rather than
deleted (D11 in `decisions.md`).
