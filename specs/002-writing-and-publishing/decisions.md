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

**ADR:** docs/adr/0007-the-markdown-editor-is-vendored.md — it clears all three legs. It is durable
(a future editor change has to overturn it), it is architectural (a dependency, a supply-chain
boundary and the package's distributed size), and it is non-obvious enough that "why is a third-party
library committed here rather than declared?" is the first thing a contributor asks. `VERSION.md`
beside the files answers what they are; the record answers why they are there at all.

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

## D14 — The privacy walk is one table every later story extends

**Ambiguous**: US-2 built a table of every address this package serves and walked each one against
three callers who should not reach it. US-3 and US-4 each add an address. Extending that table
counts as modifying a test somebody else wrote, which the guardrail flags, and the alternative is a
second parallel walk per story.

**Chosen**: one table. Each story adds its address to it and writes no second walk.

**Why defensible**: the requirement is that **no** request lacking the permission reaches a draft at
**any** address the package serves, which is a statement about the whole set. A per-story walk
would prove it address by address and never state it, and the day an address is added without a
walk beside it, nothing goes red. With one table, a new address that is not added to it is visible
as an absence in a single place.

The guardrail flag is correct and this entry is the record that clears it. What it cannot tell
apart is a test being weakened from a test being widened, so the distinction is stated here: every
change to that table so far adds a row and an assertion, and removes neither.

**Revisit if**: a story adds an address the three callers *should* reach, which would mean the
table has stopped being a list of one thing.

**ADR:** none — a test-organisation choice, local to one module and explained by the comment above
the table.

## D15 — Both admin pages answer "what would a reader be served" the same way

**Ambiguous**: the preview branched carefully — render a draft, read a published version's stored
output — and the confirmation page did not. It rendered whatever version it was given. Nothing was
written either way, so no stored evidence was ever at risk, and the suite was green.

**Chosen**: one method answers the question and both pages call it.

**Why defensible**: the confirmation page for a version that has already been published is
reachable. Its POST is refused, which is the requirement, but its GET was showing a fresh rendering
of wording somebody was already served a different rendering of. After a Markdown library upgrade
or a change to the allow list those two differ, and the page would be showing something nobody was
ever shown, on the one screen in the package that is about what goes in front of people.

Folding it into one method also removed the duplicated page setup the two views carried, so the
only difference between them is now the one that matters.

The test reinstates the defect rather than asserting the fix: with the branch removed, both the
preview's and the confirmation's assertions go red, and with it in place both pass.

**Revisit if**: a third page needs the same answer with a different rule, which would mean the
question is not one question after all.

**ADR:** none — a correction inside one class, and the rule it applies is already recorded as
Article XIII in the constitution and as ADR 0001's neighbours. Nothing downstream inherits it.

## D16 — The message catalog is regenerated from the repository root

**Ambiguous**: `makemessages` behaves differently depending on where it is run, and nothing said
which. Run from the package directory it rewrites every file reference to be relative to that
directory, so the whole file diffs for reasons unrelated to any string in it. It also writes a
creation timestamp that changes on every run, and it can mark a new string as a fuzzy match against
a similarly-worded existing one and copy that entry's translation instead of using the new text.

**Chosen**: run it from the repository root, keep the file references repository-relative as the
committed file already had them, carry no creation timestamp, and check every entry it marks fuzzy
before committing.

**Why defensible**: the convention was already in the committed file and was followed by nobody,
because it was written down nowhere — two separate pieces of work in this run rediscovered it by
producing a large diff and having it corrected. It is now a comment in the catalog's own header, which
is the one file somebody about to regenerate it has open, and which survives regeneration.

**Revisit if**: the project adopts a translation workflow that owns the file, in which case the
tool's defaults matter more than the diff.

**ADR:** none — a contributor convention, recorded in the file it governs.

## D17 — The remaining guardrail flags on the whole feature, and why each clears

**Ambiguous**: run across the whole branch rather than one story, the test guardrail reports five
flags. Two already have records. The other three needed a look before the branch could leave
convergence.

**Chosen**: all five clear. None is a test weakened to let code through.

**Why defensible**, one at a time:

`tests/test_app.py` is D11 — the previous feature's scope statement, superseded by this one, with
the half that still guards something kept.

`tests/test_admin.py` is D14 — one table of every address this package serves, extended by each
story that adds an address, never shortened.

`tests/factories.py`, `tests/conftest.py` and `tests/test_factories.py` are pure additions. A user
factory and the fixtures for each permission set this surface has to tell apart, plus the tests for
the factory. Nothing existing was changed in any of the three; the guardrail reports the file as
modified because it cannot tell an addition to a file from an edit inside it.

The fifth flag, a weakening pattern, is a false positive on the string `skip` inside
`skip_postgeneration_save = True` in the user factory's `Meta`. That setting tells `factory_boy`
not to save a second time after the hook that sets the password has already saved. It has nothing
to do with skipping a test, and there is no `skip`, `xfail` or disabled assertion anywhere on this
branch.

**Revisit if**: the guardrail grows a way to distinguish an addition from an edit, which would
remove three of these five and make the remaining two easier to see.

**ADR:** none — a triage record for one branch, not a decision anything inherits.

## D18 — A document identifier from the query string is validated before it is asked for

**Ambiguous**: starting the next version reaches the form with a document named in the query
string. That value arrives as a string and can be anything at all, and nothing checked it before
handing it to the database.

**Chosen**: anything the identifier cannot be is treated the same as a document that does not
exist. The form opens empty.

**Why defensible**: asking for a document whose identifier is not a number raises rather than
returning nothing, so a mistyped or edited link produced a server error instead of an empty form.
The person it reaches is by assumption not a developer and has done nothing wrong. Treating an
unusable identifier as "no such document" gives the same answer the feature already gives for a
document that has nothing in force, which is the ordinary case rather than an error.

Nothing was exposed by it — the value never reached SQL, because the field refused to prepare it —
so this is a broken page rather than a way in. It is fixed because a broken page is enough.

The test parametrises the identifiers that cannot work, including one shaped like an injection
attempt, and asserts each opens the form. Removing the guard turns two of them red.

**Revisit if**: another surface takes an identifier from a query string, which would make this a
shape worth sharing rather than a guard on one method.

**ADR:** none — input handling inside one method, with the requirement it serves recorded above it.

## D19 — The edge case that justifies two permissions is tested by the thing it describes

**Ambiguous**: the specification names somebody who may publish and may not write as an intended
arrangement, and D4 calls it the reason the two permissions are split at all. A fixture was built
for it during the groundwork and then never used by any test.

**Chosen**: a test that uses it, asserting both halves — such a person can put a version in force,
and cannot change a word of it.

**Why defensible**: the split is the whole of FR-014, and the case that makes it more than a
formality was the one case nothing exercised. A fixture defined and never called is also a reliable
sign that a requirement was read and not built, which is what it turned out to be here — the
behaviour was already correct, and nothing would have said so if it stopped being.

**ADR:** none — a missing test, now present.

## D20 — has_add_permission does both jobs T065 asks of it

**Ambiguous**: T065 wants a version reachable only from a document — no add control on the
changelist, and a bare request for the add form refused. Those look like two separate things: a
button to hide and a view to guard.

**Chosen**: one override, `VersionAdmin.has_add_permission(request)`, returning `False` whenever
the request names no document the same `document_from()` helper `get_changeform_initial_data()`
already uses to read one. Django calls this single method to decide both the changelist's add
control and the add view's own permission check, so nothing else has to.

**Why defensible**: a second, template-level check hiding only the button would leave the address
itself open to anyone who typed it — the button is not the boundary, the permission is. Reusing
`document_from()` means a mistyped or hostile identifier is refused the same way it is already
treated as "no document" elsewhere on this admin (D18), rather than inventing a second rule for
what counts as naming one.

The one thing this method cannot fix on its own is "Save and add another": its own request carries
the document correctly (a real, resolvable one is exactly what got it past this check), but
Django's `response_add()` redirects that button's *next* page to `request.path`, dropping the query
string. `render_change_form()` sets `show_save_and_add_another` to `False` unconditionally, which
also means a change form never offers it — already true in practice, since a change page's own
query string never names a document and this same permission check would refuse it anyway, so
nothing observable changes there.

**Revisit if**: a future surface needs to add a version from somewhere that is not a document's own
page, which would need a different way of naming one, not just a different permission check.

**ADR:** none — one method doing the one job it was already positioned to do.

## D21 — Four pre-existing tests changed because the walkthrough fixes changed what they asserted

**Ambiguous**: the walkthrough fixes (issue #17) moved and removed controls a handful of existing
tests were built against, and refuse-unless-instructed is the default for a test this work did not
author.

**Chosen**: four tests updated in place rather than left red or worked around:

- `test_the_document_page_offers_the_next_version` (T053) asserted the document page carried a
  link to the version add form. T063 moves that control to the version page and says so in its own
  "Done when": deleted, and its replacement (`test_the_document_page_offers_its_current_version_and
  _history`) asserts the add link is now absent from that page.
- `test_the_add_page_carries_the_editor_widget` reached the add view with no document named.
  T065 refuses that request outright, so the test now names one.
- `test_a_document_the_query_string_cannot_name_opens_empty` (renamed `..._is_refused`) asserted a
  mistyped or hostile identifier opened an empty form. `document_from()` already treated such an
  identifier the same as no document at all (D18); T065 extends that to `has_add_permission()`, so
  the same identifiers are now refused rather than shown an empty page, and the test's assertion is
  the inverse of what it was.
- `test_editing_the_copy_leaves_the_published_version_alone` (T054) posted straight to the add
  URL with no query string. A real browser's empty-action form submits back to the page it loaded
  from, query string included, which is what let the original GET past `has_add_permission()` in
  the first place; the test now posts to that same address instead of a bare one.

**Why defensible**: each task in the brief's own table names the exact behaviour that made the old
assertion wrong — T063 says the control "is gone from there", T065 says a nameless request "is
refused". These are not tests weakened or special-cased to pass; each now asserts the behaviour the
task itself specifies, in the same place it asserted the old one.

**ADR:** none — four assertions brought into line with a behaviour the tasks table itself changed.
