# Feature Specification: Writing and publishing a document without a developer

**Feature Branch**: `002-writing-and-publishing`

**Created**: 2026-09-21

**Status**: Draft

**Serves**: G1 · **Roadmap**: R1 · **Issue**: #5 · **Depends on**: FS-001 (#4)

**Input**: The reason to keep these documents in the database rather than in the codebase is so that
changing one does not need an engineer, a pull request or a deployment. Whoever is responsible for
the wording, often not a developer and sometimes not an employee, should be able to write the next
version, read it back as it will appear to the public, and put it live when they are happy with it.
Until they publish it, the draft is theirs alone: invisible to the public, carrying no legal weight,
and safe to leave half-finished. Publishing is the deliberate act that changes that, and it should
feel like one.

## Scope

FS-001 made publishing possible and permanent. This is the surface that makes it something a person
can do.

The person doing it is a **compliance editor**: whoever is responsible for the wording of a site's
legal documents. Often not a developer, sometimes not an employee, and not assumed to know Markdown
or anything else about how the site is built. Everything here is designed for them.

This feature calls into the rules FS-001 specified and never re-implements or softens them. The
public pages a visitor reads are R2. The summary of what changed between versions is R6. Telling
anybody that a publish happened is #12.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Write a version without knowing Markdown (Priority: P1)

A compliance editor opens a new version and types the document the way they would type it anywhere
else. Headings, bold, italics, lists, links and quotes are buttons, not syntax they have to learn.
The buttons stop there. No images, no embeds, no tables, no tagging, no raw HTML. A legal document
needs structured prose and nothing more, and every button that exists is a button somebody has to
be supported in using.

**Why this priority**: This is the whole of G1's second half. A version that only a developer can
write leaves the documents in the codebase in every way that matters, whichever database row they
happen to sit in.

**Independent Test**: Give somebody who has never written Markdown the editor, have them produce a
document with headings, emphasis, a list and a link without typing a single Markdown character, and
confirm what is stored is ordinary Markdown.

**Acceptance Scenarios**:

1. **Given** a compliance editor writing a new version, **When** they use the editor's formatting
   controls, **Then** the document gains headings, bold, italics, lists, links and block quotes
   without them typing Markdown syntax.
2. **Given** the editor, **When** its available controls are inspected, **Then** there is no control
   for an image, an embed, a table, a tag or raw HTML.
3. **Given** a compliance editor who does know Markdown, **When** they type it directly, **Then** it
   works, because the stored content is ordinary Markdown either way.
4. **Given** every control the editor offers, **When** the output of each is published, **Then**
   none of it is stripped, because the controls and the allow list FS-001 specified agree.
5. **Given** authored content the allow list would strip, **When** it is written anyway by typing it
   by hand, **Then** the loss is visible in the preview rather than discovered after publication.

---

### User Story 2 - A draft belongs to its author until it is published (Priority: P1)

A half-written version is nobody's business but the person writing it. It is invisible to the
public, it carries no legal weight, and it can be revised over weeks, left alone, or thrown away.
Nothing about it is exposed at any address a visitor can reach, and nothing about it appears
anywhere a member of the public looks.

**Why this priority**: The freedom to leave something half-finished is what makes a draft useful.
An author who suspects an unfinished policy might be reachable writes differently, or writes it
somewhere else and pastes it in at the end, which is the behaviour this package exists to replace.

**Independent Test**: Create a draft, confirm it is revisable and discardable, and confirm no
request without the relevant permission can reach it by any address the package serves.

**Acceptance Scenarios**:

1. **Given** a draft, **When** its author returns to it days later, **Then** it is as they left it
   and still fully editable.
2. **Given** a draft, **When** its author discards it, **Then** it is gone, and no other version of
   the document is affected.
3. **Given** a draft, **When** somebody without the permission to work on documents attempts to
   reach it, **Then** they cannot, at any address the package serves.
4. **Given** a document whose only version is a draft, **When** a visitor looks at the site,
   **Then** nothing about the document or its draft is visible to them.
5. **Given** several drafts of the same document, **When** a compliance editor lists them, **Then**
   all of them are there and each is separately editable.

---

### User Story 3 - Read it back the way the public will see it (Priority: P1)

Before publishing, the compliance editor sees the version rendered exactly as the published page
will render it. Not the editor's own approximation of the formatting, but the real output produced
by the real rendering, so that what they approve is what the public gets.

**Why this priority**: Publishing cannot be undone. The preview is the last moment anybody can
catch a broken heading or a mangled clause, and an approximate preview turns that last moment into
a false reassurance.

**Independent Test**: Write a version exercising every control the editor offers, preview it, then
publish it, and confirm the published output matches what the preview showed.

**Acceptance Scenarios**:

1. **Given** a draft, **When** its author previews it, **Then** the rendering they see is produced
   by the same rendering the published page will use.
2. **Given** a previewed draft, **When** it is subsequently published, **Then** the stored output
   matches what the preview showed.
3. **Given** a draft containing content the allow list strips, **When** it is previewed, **Then**
   the preview shows it stripped, because the preview does not flatter the draft.
4. **Given** a preview, **When** somebody without the permission to work on documents requests it,
   **Then** they are refused.
5. **Given** the editor's own inline formatting display, **When** it is compared with the preview,
   **Then** they are understood to be two different things: the first is a writing aid, the second
   is what the public will get.

---

### User Story 4 - Publishing is deliberate, and there is no way back (Priority: P1)

Putting a version live is the one irreversible act in the package, and it is presented as one. It
is a distinct action rather than a side effect of saving, it asks for confirmation, and the
confirmation says plainly that the wording cannot be changed afterwards and that a correction means
another version. It needs a permission of its own, because writing a draft and making something
legally binding are different levels of trust. Once done, the admin offers no form that would edit
what was published.

**Why this priority**: An author who publishes by accident cannot undo it, and the package's
central promise is precisely that they cannot. The interface has to carry the weight the data model
already carries.

**Independent Test**: Attempt to publish as somebody holding only the permission to write drafts
and confirm the refusal, then publish with the right permission and confirm the confirmation step
names the consequence, then confirm the published version presents no editable form.

**Acceptance Scenarios**:

1. **Given** a compliance editor holding only the permission to write drafts, **When** they attempt
   to publish, **Then** they are refused and the version stays a draft.
2. **Given** a compliance editor holding the permission to publish, **When** they publish, **Then**
   they are asked to confirm first, and the confirmation states that the wording cannot be changed
   afterwards and that a correction means another version.
3. **Given** the confirmation step, **When** it is declined, **Then** nothing is published and the
   draft is untouched.
4. **Given** an ordinary save of a draft, **When** it completes, **Then** nothing has been
   published, because publishing is never a side effect of saving.
5. **Given** a published version, **When** a compliance editor opens it, **Then** they can read it
   in full and there is no editable form, rather than a form whose save is refused.
6. **Given** a version whose content renders to nothing, **When** publication is attempted, **Then**
   the refusal FS-001 specifies reaches the author as an explanation they can act on.
7. **Given** a version that is already published, **When** publication is attempted again, **Then**
   the refusal reaches the author the same way.
8. **Given** any text this feature shows a person, **When** it is read, **Then** nothing in it says
   or implies that publishing makes the site compliant with anything.

---

### User Story 5 - Start the next version from the one in force (Priority: P2)

Most rewordings are edits to what is already there. A compliance editor asked to change one clause
starts from the current wording rather than from an empty box, because retyping a policy to fix a
sentence is how new errors arrive.

**Why this priority**: A convenience rather than a capability, and the feature is usable without
it. It is also the one most likely to be missed, because the person specifying it is not the person
who will retype a four-thousand-word policy.

**Independent Test**: With a document that has a version in force, begin the next version and
confirm it opens holding the current wording, then confirm changing it leaves the published version
untouched.

**Acceptance Scenarios**:

1. **Given** a document with a version in force, **When** a compliance editor begins the next
   version, **Then** it opens holding the current wording, ready to be edited.
2. **Given** a new version started from the current wording, **When** it is edited, **Then** the
   published version it was copied from is unchanged.
3. **Given** a document with no version in force, **When** a compliance editor begins a version,
   **Then** it opens empty, and this is the ordinary case for a new document.

---

### Edge Cases

- An author writes Markdown by hand that the allow list strips. The preview shows the loss, so it
  is caught before publication rather than after, when it cannot be corrected.
- An author leaves a draft for weeks and comes back to find the document has had another version
  published in the meantime. Their draft is still a draft and still publishable, and publishing it
  supersedes whatever is in force at that moment.
- Somebody holding the permission to publish but not to write drafts. They can publish what exists
  and write nothing, which is an unusual but coherent arrangement for a site where wording is
  approved by somebody other than its author.
- An author publishes and immediately realises there is a typo. There is no undo. They write and
  publish the next version, and the typo remains readable forever, which is the cost the package
  accepts deliberately.
- A document is deleted while it has only drafts. Permitted, because nothing has been put in front
  of anybody.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A compliance editor MUST be able to create a document and write versions of it
  without a code change, a migration or a deployment. *(US-1)*
- **FR-002**: Writing a version MUST offer formatting controls for headings, bold, italics, lists,
  links and block quotes, so that no Markdown syntax has to be typed. *(US-1)*
- **FR-003**: The formatting controls MUST NOT include images, embeds, tables, tagging or raw HTML.
  *(US-1)*
- **FR-004**: The set of formatting controls offered MUST agree with the allow list FS-001 applies
  at publication, so that no control produces content that is later stripped. *(US-1)*
- **FR-005**: Content stored for a version MUST be ordinary Markdown, so an author who prefers to
  type it directly is not obstructed. *(US-1)*
- **FR-006**: A draft MUST remain editable and discardable for as long as it is a draft. *(US-2)*
- **FR-007**: A draft MUST NOT be reachable, at any address the package serves, by anybody lacking
  the permission to work on documents. *(US-2)*
- **FR-008**: A document with no published version MUST be invisible to visitors. *(US-2)*
- **FR-009**: A compliance editor MUST be able to see every version of a document and its state.
  *(US-2, US-5)*
- **FR-010**: A draft MUST be previewable, rendered by the same rendering the published page uses.
  *(US-3)*
- **FR-011**: A preview MUST show content the allow list strips as stripped, rather than as
  authored. *(US-3)*
- **FR-012**: A preview MUST be refused to anybody lacking the permission to work on documents.
  *(US-3)*
- **FR-013**: Publishing MUST be a distinct action, never a side effect of saving a draft. *(US-4)*
- **FR-014**: Publishing MUST require a permission separate from the one that allows writing
  drafts. *(US-4)*
- **FR-015**: Publishing MUST ask for confirmation, and the confirmation MUST state that the
  wording cannot be changed afterwards and that a correction means another version. *(US-4)*
- **FR-016**: Declining the confirmation MUST leave the draft untouched. *(US-4)*
- **FR-017**: A published version MUST be readable in full and MUST present no editable form.
  *(US-4)*
- **FR-018**: Refusals raised by the rules FS-001 specifies, including publishing a version that
  renders to nothing and publishing one that is already published, MUST reach the author as an
  explanation they can act on rather than as an unhandled error. *(US-4)*
- **FR-019**: No text this feature shows a person may state or imply that publishing makes a site
  compliant with any regulation. *(US-4)*
- **FR-020**: Every string this feature shows a person MUST be translatable. *(US-1..US-5)*
- **FR-021**: Beginning a new version of a document that has one in force MUST offer the current
  wording as the starting point. *(US-5)*
- **FR-022**: Editing a version started from the current wording MUST leave the published version it
  was copied from unchanged. *(US-5)*

### Key Entities

- **Compliance editor**: Whoever is responsible for the wording of a site's legal documents. Not
  assumed to be a developer, an employee, or familiar with Markdown. Holds the permission to work
  on documents, and separately may hold the permission to publish. This term is new and joins
  `CONTEXT.md` when the feature is built.
- **Draft** and **Version**: as defined in `CONTEXT.md` and specified in FS-001. This feature adds
  no state to either.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person who has never written Markdown produces a document with headings, emphasis,
  a list and a link without typing a Markdown character.
- **SC-002**: Every formatting control the editor offers survives publication intact, with no
  control whose output the allow list strips.
- **SC-003**: No request lacking the permission to work on documents reaches a draft or a preview,
  at any address the package serves.
- **SC-004**: The output stored at publication is identical to what the preview showed for the same
  content.
- **SC-005**: Publishing cannot be reached without its own permission, and cannot happen without a
  confirmation that names the consequence.
- **SC-006**: A published version offers no editable form anywhere in the admin.
- **SC-007**: Both refusals FS-001 raises at publication reach the author as readable explanations.
- **SC-008**: No string in the feature claims compliance, and every string is translatable.

## Clarifications

### Session 2026-09-21

- **Q**: Where does this surface live, the Django admin or a bespoke editor at its own addresses? →
  **A**: The Django admin. It is where a site's staff already go, it comes free with the framework,
  and the account-area surface in R9 serves a different audience entirely.
- **Q**: Is the author assumed to know Markdown? → **A**: No. The editor offers formatting controls
  so that no syntax has to be typed, and the stored content is ordinary Markdown regardless
  (FR-002, FR-005).
- **Q**: How far does the editor's toolbar go? → **A**: Headings, bold, italics, lists, links and
  block quotes. No images, embeds, tables, tagging or raw HTML. A legal document needs structured
  prose, and every control offered is one somebody has to be supported in using.
- **Q**: Is the editor's own inline formatting display the same thing as the preview? → **A**: No.
  The inline display is a writing aid belonging to the editor control. The preview is the real
  rendering the published page will use, and it is what an author approves before publishing
  (FR-010).
- **Q**: Are writing a draft and publishing one permission or two? → **A**: Two. Writing wording and
  making it legally binding are different levels of trust, and a site that wants one person to do
  both grants both (FR-014).

## Assumptions

- The surface is the Django admin. No bespoke editor mounted at its own addresses.
- Access is governed by Django's own permissions, per model.
- A published version's page in the admin is readable with no editable form at all, rather than a
  form whose fields are disabled or whose save is refused.
- Two people editing the same draft is not solved here. The last save wins, as it does everywhere
  in the Django admin, and a solution waits for somebody to report the problem.
- A draft may be previewed for as long as it exists. An unpublished wording is reachable by anybody
  holding the permission to work on documents, and by nobody else.
- Telling anyone that a publish happened is out of scope and tracked as #12.
- The admin is a different surface from the site, with its own conventions. The requirement that
  pages look like the rest of the site applies to R2, not here.
- `CONTEXT.md` gains a **Compliance editor** entry when this feature is built. It cannot arrive in
  the specification's own pull request, which carries the specification directory and nothing else.
