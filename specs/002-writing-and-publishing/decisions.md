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

## D5 — Concurrent editing of one draft is not solved

**Ambiguous**: two compliance editors open the same draft and the second save overwrites the first.

**Chosen**: not solved. The last save wins.

**Why defensible**: Sam's ruling, 2026-09-21. This is the Django admin's behaviour on every model
in every project, so a document behaving differently from everything else in the same interface is
its own surprise. The blast radius is also bounded by the rest of the design: the loss is confined
to a draft, which by definition has no legal weight and can be rewritten, and no published wording
is reachable by this or any other route. If it is reported as a real problem, it gets a real
solution then.

## D6 — A published version presents no editable form at all

**Ambiguous**: FS-001 guarantees a published version's wording cannot change, so an admin form over
one is safe from a data point of view. The question is whether it should exist.

**Chosen**: no editable form. The published version is readable, and that is all.

**Why defensible**: a form that accepts keystrokes and then refuses the save teaches an author that
the interface is unreliable, and it wastes the work they did before finding out. Disabled fields
are barely better, because they invite the question of how to enable them. Offering nothing to edit
states the rule instead of enforcing it after the fact. The safety of the data is FS-001's job and
it is already done. This is about not lying to the person in front of the screen.

## D7 — Refusals from the rules reach the author as explanations

**Ambiguous**: FS-001 specifies two refusals at publication, for content that renders to nothing and
for a version already published. It says nothing about how a person learns of them.

**Chosen**: both reach the author as an explanation they can act on.

**Why defensible**: a rule enforced at the data layer surfaces as an unhandled error unless
something catches it, and an unhandled error in the admin is a traceback or a five-hundred page.
The compliance editor these refusals will reach is by assumption not a developer. Catching them is
the whole of what this surface adds over calling the model directly, so leaving it out would mean
shipping the surface without the part that makes it a surface.
