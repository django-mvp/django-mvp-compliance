# Decisions — 002 Writing and publishing a document without a developer

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — The Django admin, not a bespoke editor

**Ambiguous**: the issue says the person writing is often not a developer, which could argue for a
purpose-built editing surface at its own addresses rather than the framework's admin.

**Chosen**: the Django admin.

**Why defensible**: a site's staff already go there, and a second staff-facing surface with its own
navigation and its own permissions is a second thing to explain. The admin also comes with the
permission model, the list views and the audit of who changed what, none of which is worth
rebuilding for a handful of documents. The audience that genuinely needs a non-admin surface is the
signed-in member of the public looking at their own record, and that is R9.

The cost is real and worth naming: the admin looks like the admin, so a compliance editor who is
not otherwise a staff user meets an interface built for developers. If that turns out to be the
barrier the issue is worried about, the answer is a dedicated surface as its own feature, not a
gradual reinvention of one inside this one.

**ADR:** none — scope, not architecture. The choice of surface is recorded in `spec.md`'s Clarifications and its assumptions, and a later bespoke surface would be a new feature beside this one rather than an overturning of it.

## D2 — The author is not assumed to know Markdown, and the toolbar is deliberately short

**Ambiguous**: whether the editor is a plain text area holding Markdown, a rich editor, or
something between.

**Chosen**: a basic editor with formatting controls for headings, bold, italics, lists, links and
block quotes. No images, embeds, tables, tagging or raw HTML. The stored content stays ordinary
Markdown.

**Why defensible**: Sam's ruling, and the reasoning holds up on inspection. A legal document is
structured prose, and the controls left out are the ones that either have no place in one or
produce content the allow list would strip anyway. Every control offered is a control somebody has
to be supported in using, and a toolbar that can produce something publication then removes is a
worse experience than no toolbar at all.

This is the reason FR-004 exists. The toolbar and the allow list FS-001 applies are two statements
of the same decision, and they have to be kept in agreement rather than each maintained on its own.
A button whose output is silently stripped at publication is the specific defect worth designing
against.

**ADR:** none — a product ruling about what the toolbar offers, durable but not architectural. FR-002 to FR-004 carry it, and T018 keeps it true.

## D3 — The editor's inline display is not the preview

**Ambiguous**: most Markdown editor controls ship with their own preview, which invites treating
that as the preview this feature owes the author.

**Chosen**: two distinct things. The editor's inline display is a writing aid. The preview is the
real rendering the published page will use, and it is what an author approves before publishing.

**Why defensible**: the editor control renders with its own library and its own assumptions, and it
knows nothing about the allow list. An author who approves that display has approved something the
public will never see. Publishing cannot be undone, so the last look before it has to be the
accurate one. The inline display stays because it genuinely helps while writing, and the
specification separates them so that nobody later treats one as satisfying the other.

**ADR:** none — a distinction the specification itself draws and the code expresses directly. Nothing downstream inherits a structure from it.

## D4 — Writing and publishing are two permissions

**Ambiguous**: whether a compliance editor who can write a version can necessarily publish it.

**Chosen**: two permissions. A site wanting one person to do both grants both.

**Why defensible**: writing wording and making it legally binding are different levels of trust,
and the split is free to offer while impossible to retrofit without breaking whatever configuration
sites have already made. It also matches how the work actually happens where it matters: the person
who drafts a privacy policy and the person who signs it off are frequently not the same person, and
sometimes the first is not an employee at all.

The unusual combination it allows, publish without write, is coherent rather than a defect. It
describes an approver who signs off wording somebody else prepared.

**ADR:** none — a permission split is recorded where it is declared, on `Version.Meta.permissions`, and README explains who needs which. No cross-cutting structure follows from it.

## D5 — Concurrent editing of one draft is not solved

**Ambiguous**: two compliance editors open the same draft and the second save overwrites the first.

**Chosen**: not solved. The last save wins.

**Why defensible**: Sam's ruling, 2026-09-21. This is the Django admin's behaviour on every model
in every project, so a document behaving differently from everything else in the same interface is
its own surprise. The blast radius is also bounded by the rest of the design: the loss is confined
to a draft, which by definition has no legal weight and can be rewritten, and no published wording
is reachable by this or any other route. If it is reported as a real problem, it gets a real
solution then.

**ADR:** none — an absence rather than a decision anything is built on. Revisiting it changes nothing already written.

## D6 — A published version presents no editable form at all

**Ambiguous**: FS-001 guarantees a published version's wording cannot change, so an admin form over
one is safe from a data point of view. The question is whether it should exist.

**Chosen**: no editable form. The published version is readable, and that is all.

**Why defensible**: a form that accepts keystrokes and then refuses the save teaches an author that
the interface is unreliable, and it wastes the work they did before finding out. Disabled fields
are barely better, because they invite the question of how to enable them. Offering nothing to edit
states the rule instead of enforcing it after the fact. The safety of the data is FS-001's job and
it is already done. This is about not lying to the person in front of the screen.

**ADR:** none — local to this surface. It is one permission method returning `False`, and the requirement it serves is FR-017.

## D7 — Refusals from the rules reach the author as explanations

**Ambiguous**: FS-001 specifies two refusals at publication, for content that renders to nothing and
for a version already published. It says nothing about how a person learns of them.

**Chosen**: both reach the author as an explanation they can act on.

**Why defensible**: a rule enforced at the data layer surfaces as an unhandled error unless
something catches it, and an unhandled error in the admin is a traceback or a five-hundred page.
The compliance editor these refusals will reach is by assumption not a developer. Catching them is
the whole of what this surface adds over calling the model directly, so leaving it out would mean
shipping the surface without the part that makes it a surface.

Both refusals raise the same exception. `publish()` raises `PublishError` on each of them, and the
save it performs runs while the stored row is still a draft, so the immutability guard returns
before it can raise anything. One `except` branch covers both, and a second would be unreachable.

**ADR:** none — local to this surface. Catching two named exceptions in one view inherits nothing downstream.

## D8 — EasyMDE, vendored into the package

**Ambiguous**: D2 settles what the toolbar offers and says nothing about what draws it. A basic
editor with formatting controls can be anything from a hundred lines over a text area to a full
editing framework.

**Chosen**: EasyMDE 2.21.0, its two distributed files committed to the repository under
`static/mvp_compliance/vendor/easymde/` beside the upstream licence and a note recording the
version and the hash of each file. No Python dependency, no content delivery network.

**Why defensible**: the specification decides this one itself. US-3 scenario 5 compares "the
editor's own inline formatting display" with the preview, which is only a meaningful comparison
against an editor that renders formatting while it is typed — a toolbar over a plain text area has
no such display and the scenario would have nothing on one side of it. Of the controls that do,
EasyMDE takes its toolbar as an explicit list, so the set FR-003 forbids does not exist rather than
being hidden, and it writes ordinary Markdown back to the text area, which FR-005 requires.

Vendoring rather than fetching follows from Article XV: a third-party asset tag would let somebody
else change what runs inside an authenticated session on a site this package is installed on. A
Python wrapper package was considered and rejected — it adds a dependency and a second opinion about
the toolbar in exchange for the same two files this package would still have to configure.

The cost is 340 KB of minified JavaScript in the repository, and a refresh is a manual step. Both
are stated in `plan.md`'s Complexity Tracking rather than passed over.

`django-markdownx`, which the FairDM project already runs, is rejected on the requirements rather
than on taste: it ships no formatting toolbar at all, which is FR-002's whole purpose, and it does
ship drag-and-drop image upload, which FR-003 forbids.

**ADR:** none — a vendoring choice, recorded where it lands. `VERSION.md` beside the files says what
they are and where they came from, which is what somebody upgrading them needs; nothing else in the
package inherits a structure from it.

## D9 — The toolbar's icons are ours, and there is no icon font

**Ambiguous**: EasyMDE's documentation does not foreground the fact that it ships no icons. Its
stylesheet contains none, while its script writes Font Awesome 4 class names into every button it
builds. Dropped into the admin with only the distributed files, every button renders as an empty
box.

**Chosen**: each button is declared with its own class name, and the package's own stylesheet draws
it from an inline SVG. Six icons. No icon font, no web font, no external request.

**Why defensible**: a whole icon font for six buttons is a poor trade, and nothing else in this
package has a use for one. Declaring the buttons ourselves also makes FR-003 checkable at the only
place it matters — the markup a request receives — because the button set becomes a single
declaration that travels to the page as data.

**ADR:** none — a presentation detail of one widget, with no consumer beyond its own stylesheet.

## D10 — The preview renders what is stored, not what is in the editor

**Ambiguous**: FR-010 requires a preview produced by the rendering the published page will use. It
does not say whether the preview reads the version as saved or the text currently in the author's
editor.

**Chosen**: the version as saved. An author saves, then previews.

**Why defensible**: SC-004 requires that what publication stores is identical to what the preview
showed, and only one of the two designs makes that true by construction. Publication renders the
stored Markdown, so a preview of the editor's unsaved buffer would show an author something that
publication may never produce — they preview, keep typing, then publish, and what goes live is not
what they approved. Reading the stored row means the preview and `publish()` take the same field
through the same renderer, with no window in which they can disagree.

The cost is one extra save on a path that already ends in an irreversible act, and it is the order
the Django admin imposes everywhere else.

A published version's preview reads its stored HTML rather than rendering again, because Article
XIII forbids re-rendering one.

**ADR:** none — the requirement it serves is SC-004 and the code expresses it in one view. Nothing
downstream inherits it.

## D11 — FS-001's assertion that no admin exists is narrowed here, not deleted

**Ambiguous**: FS-001 shipped `tests/test_app.py::test_it_ships_no_admin_forms_views_or_urls` and
`test_it_registers_nothing_in_the_admin`, which its D5 wrote to hold its own scope. This feature is
the one that adds all four, so both assertions now fail by design.

**Chosen**: narrow rather than remove. The first becomes `test_it_registers_no_public_urls`, which
keeps the half that is still true and still load-bearing — the package serves no address a member
of the public can reach, which is FR-008. The second is replaced by its opposite, asserting both
models are registered. Each carries a comment naming this feature as what superseded FS-001's D5.

**Why defensible**: FS-001's specification named the authoring screens as issue #5 and scoped itself
to the model layer deliberately, so this is a specification superseding an earlier one that said it
would, not a test weakened to let code through. The part of the assertion that survives is the part
that still guards something: no public surface exists until R2 builds one, and a test saying so is
worth more than one saying no admin exists.

`forge tamper-check` flags the change, correctly — it cannot tell a supersession from a weakening.
This entry is the triage record that clears the flag.

**ADR:** none — a test-scope correction tied to one feature boundary. The reasoning belongs beside
the test, and it is in the comment the tests carry.

## D12 — Publishing is a model permission on `Version`, not a group or a setting

**Ambiguous**: D4 settles that writing and publishing are two permissions. It does not say how the
second one is expressed.

**Chosen**: `Version.Meta.permissions` declares `publish_version`, which Django creates alongside
its four automatic ones.

**Why defensible**: it lands in the ordinary permission list of the ordinary user admin, so a site
grants it the same way it grants everything else, and a group or a setting would be a second
mechanism to learn for one permission. It also gives D4's unusual-but-coherent case a natural
expression: a user holding `publish_version` without `change_version` can publish what exists and
write nothing, with no special handling anywhere.

**ADR:** none — one line on a model `Meta`, documented in the README where a site administrator will
look for it.

## D13 — The edge case about deleting a document holding only drafts is left to Sam

**Ambiguous**: this specification's Edge Cases section says that deleting a document while it holds
only drafts is "permitted, because nothing has been put in front of anybody". FS-001 delivered the
opposite, deliberately: `Version.document` is `on_delete=PROTECT`, so a document holding any version
at all refuses deletion, and a document created by mistake is removed by discarding its drafts
first and then deleting it. That choice is FS-001's D8 and it carries an accepted architecture
decision record, `docs/adr/0002-document-deletion-is-refused-by-the-foreign-key.md`.

The two cannot both be true.

**Chosen**: nothing is built here, the delivered behaviour stands, and the conflict goes to Sam as
a question rather than being settled inside this run.

**Why defensible**: this is not a gap in the plan, it is a later specification contradicting an
accepted architecture decision, and overturning one of those is not a plan edit. Three things
decide which way to lean while he answers.

Nothing in this feature is measured by it. No functional requirement, no acceptance scenario and no
success criterion mentions deleting a document — every requirement FS-002 will be judged against is
untouched whichever way it goes.

The behaviour the edge case asks for is already reachable, at the cost of one step: discard the
drafts, then delete the document. FS-001 ships a passing test for exactly that path.

Building it means routing around the guard rather than relaxing it. `PROTECT` is enforced by
Django's deletion collector, which refuses before a confirmation page is ever offered, so the
admin would need to override both the collection and the deletion to get past it — two overrides
reintroducing precisely the route ADR 0002 records as the one that must not exist to be missed.

**What would change if he rules the other way**: a `DocumentAdmin` that overrides
`get_deleted_objects()` and `delete_model()` to remove a document's drafts before the document, a
test that a document holding a published version is still refused, an ADR superseding 0002, and
the amendment of FS-001's `test_deleting_a_document_holding_a_version_is_refused`. Small work,
and cheaper once he has said which behaviour he wants than after the wrong one is built.

**ADR:** none — this decision builds nothing. The architectural record that governs the question is
ADR 0002, which stands unamended; if Sam overturns it, that is a new ADR superseding it.
