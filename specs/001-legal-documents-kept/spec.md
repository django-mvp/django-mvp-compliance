# Feature Specification: Legal documents kept as versioned records

**Feature Branch**: `001-legal-documents-kept`

**Created**: 2026-09-21

**Status**: Draft

**Serves**: G1, G2, G6 · **Roadmap**: R1 · **Issue**: #4

**Input**: A site runs several legal documents at once, and each one gets rewritten over the years.
All of them are held in one place, each keeping every wording it has ever had, with one of those
wordings being the one currently in force. Once a wording has been put in front of people it stops
being something anyone can quietly edit, because people are agreeing to it and a record of what
they agreed to is worthless if the text behind it can move. Correcting a published document means
issuing the next version of it, however small the change.

## Scope

This is the foundation the rest of the package sits on: a document that has a lasting identity, a
sequence of versions underneath it, and a publishing step that puts one of them in force and
freezes it there.

It is the rules, not the screens. This feature adds no admin, no forms, no pages and no addresses.
The screens where someone writes a version, reads it back and publishes it are issue #5. Addresses
and rendered pages are R2. Acceptance records are R3.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Several documents, each with its own history (Priority: P1)

A site needs a privacy policy, a set of terms and a cookie policy at the same time, and it needs
each of them to accumulate its own sequence of wordings over the years without interfering with
the others. A document is the thing with the lasting identity. It holds no wording itself: every
word lives in one of its versions.

**Why this priority**: Nothing else in the package has anything to attach to until a document and
its versions exist. It is also the whole of G6 on its own, because handling four document types
identically means having no document type at all.

**Independent Test**: Create three documents, give each of them two versions, and confirm each
document reports only its own versions in its own order and that no operation on one document
reaches another.

**Acceptance Scenarios**:

1. **Given** an empty site, **When** three documents are created with distinct names, **Then** all
   three exist side by side and each reports an empty sequence of versions.
2. **Given** a document, **When** versions are added to it one after another, **Then** the document
   reports them in the order they were added.
3. **Given** two documents each holding versions, **When** a version is added to one of them,
   **Then** the other document's sequence of versions is unchanged.
4. **Given** a document, **When** its wording is looked for on the document itself, **Then** there
   is none to find, because wording belongs to versions.

---

### User Story 2 - Publishing puts exactly one version in force (Priority: P1)

A version starts life as a draft. A draft has no legal standing, is invisible to readers, and can
be edited or thrown away freely. Publishing is the deliberate step that changes that: the version
becomes the one in force, and whichever version was in force before it becomes superseded. A
document has one version in force at a time, never two and never a moment with none once it has
published anything.

**Why this priority**: This is the lifecycle every other feature reads. R2 shows the version in
force, R3 records agreement to it, R5 measures people against it. Without a single unambiguous
answer to "which one is in force", none of them has a question to ask.

**Independent Test**: Publish two versions of one document in sequence and confirm that after each
publish the document names exactly one version as in force, that the replaced one is marked
superseded, and that a published version cannot be returned to draft.

**Acceptance Scenarios**:

1. **Given** a newly created version, **When** it is inspected, **Then** it is a draft with no
   standing and is not the version in force.
2. **Given** a draft, **When** its wording is changed, **Then** the change is kept, because a draft
   is freely editable.
3. **Given** a draft, **When** it is discarded, **Then** it is gone, because a draft has no legal
   meaning to preserve.
4. **Given** a document with no published version, **When** its first draft is published, **Then**
   that version is the one in force and the document has no superseded versions.
5. **Given** a document with a version in force, **When** a second version is published, **Then**
   the second is in force and the first is superseded.
6. **Given** a document with a version in force, **When** it is asked which version is in force,
   **Then** exactly one version answers.
7. **Given** two publishes attempted against the same document at the same moment, **When** both
   complete, **Then** the document still reports exactly one version in force.
8. **Given** a published version, **When** any attempt is made to return it to draft or to make a
   superseded version current again, **Then** the package offers no way to do it.
9. **Given** a version that is already published, **When** publishing is attempted again, **Then**
   it is refused and nothing about the document changes.

---

### User Story 3 - A published wording can never change (Priority: P1)

The reason these documents live in the database rather than the repository is evidence, and
evidence that can be edited is not evidence. Once a version is published, its wording is fixed for
good, through every route this package offers: ordinary use, a shell session, a management command,
a data migration the package ships. A correction of any size is the next version.

**Why this priority**: This is the design centre and the one property the existing packages in this
space do not have. Everything downstream inherits its worth from it. An acceptance record pointing
at a version whose text can move is worth nothing.

**Independent Test**: Publish a version, then attempt to change its wording through every route the
package offers, and confirm each attempt fails loudly and leaves the stored wording untouched.

**Acceptance Scenarios**:

1. **Given** a published version, **When** its wording is changed and saved, **Then** the attempt
   fails with an error and the stored wording is unchanged.
2. **Given** a published version, **When** the change is attempted outside ordinary use, from a
   shell or a management command or a data migration the package ships, **Then** it fails the same
   way, because the rule lives with the data and not with any one caller.
3. **Given** a published version, **When** it is superseded by a later publish, **Then** its
   wording is still unchanged, because becoming superseded is a change of standing and not of text.
4. **Given** a published version, **When** deletion of it is attempted, **Then** the package offers
   no way to do it.
5. **Given** a document that has published at least one version, **When** deletion of the document
   is attempted, **Then** the package offers no way to do it, because deleting the document would
   destroy the published versions underneath it.
6. **Given** a published version whose wording contains an error, **When** the error is corrected,
   **Then** the correction exists as a new version and the erroneous one is still readable.

---

### User Story 4 - What a reader will be served is fixed at publication (Priority: P2)

A version carries two things: the markup its author wrote, and the output a reader is served. The
second is produced once, at the moment of publication, and stored. It is never produced again. A
markup library upgrade, a different set of extensions or a changed sanitiser allow list can all
turn identical source into different output, which would quietly change what the record says a
person was shown.

**Why this priority**: G2 promises a person can be shown what they agreed to exactly as they saw
it, and producing the output fresh years later breaks that promise without anyone noticing. P2
rather than P1 because the three stories above are what make a version exist and stay put, and this
one makes what it holds trustworthy.

**Independent Test**: Publish a version, record the output stored for it, change the markup
rendering configuration, and confirm the stored output is identical afterwards.

**Acceptance Scenarios**:

1. **Given** a draft holding authored markup, **When** it is published, **Then** the output a
   reader will be served is produced at that moment and stored alongside the source.
2. **Given** a published version, **When** its stored output is read at any later time, **Then** it
   is identical to what was stored at publication.
3. **Given** a published version, **When** the markup rendering configuration changes, **Then** the
   stored output does not change.
4. **Given** authored markup containing content the allow list rejects, **When** the version is
   published, **Then** the rejected content is absent from the stored output.
5. **Given** a draft, **When** it is inspected before publication, **Then** it has no stored output,
   because nothing has been served to anybody.

---

### User Story 5 - Every version stays retrievable, forever (Priority: P2)

Somebody who agreed to the wording from two years ago is entitled to read that wording. A
superseded version is not an old copy kept out of politeness, it is the thing a record points at.
This story is the way the rest of the package asks: give me the version in force, give me this
particular version, give me everything this document has ever said, in order.

**Why this priority**: R2 needs it to render a version, R3 needs it to resolve what a record points
at, and R10 needs it to show what preceded what. P2 because the storing has to be right before the
retrieval has anything worth returning.

**Independent Test**: Publish three versions of one document in sequence, then retrieve each one
individually and the whole sequence, and confirm every wording and every stored output comes back
intact and in order.

**Acceptance Scenarios**:

1. **Given** a document with several published versions, **When** its full sequence is requested,
   **Then** every version it has ever published comes back in order.
2. **Given** a superseded version, **When** it is retrieved, **Then** its wording and its stored
   output are exactly what they were at publication.
3. **Given** a document with a version in force, **When** the version in force is requested,
   **Then** exactly that version comes back.
4. **Given** a document with no published version, **When** the version in force is requested,
   **Then** the answer is that there is none, and this is a normal result rather than an error.
5. **Given** a document with both drafts and published versions, **When** the published history is
   requested, **Then** the drafts are absent from it.

---

### Edge Cases

- Two publishes reach the same document at the same moment. One wins and one is refused, and the
  document never reports two versions in force.
- A document is created and never published. It has no version in force, it is invisible to
  readers, and asking for its current wording returns nothing rather than failing.
- A version is published twice. The second attempt is refused and nothing about the document moves.
- The only draft of a document is discarded, leaving the document with no versions at all. This is
  the same state as a freshly created document.
- An author needs the wording from three versions ago back. They publish it again as a new version.
  The package offers no route that makes an old version current a second time.
- Authored markup renders to empty output. Publication is refused rather than putting an empty
  document in force.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST allow a site to hold any number of legal documents at once, each
  with a name and an identity that survives every rewording. *(US-1)*
- **FR-002**: A document MUST hold no wording of its own. All wording MUST live in its versions.
  *(US-1)*
- **FR-003**: Every version MUST belong to exactly one document, and versions MUST carry an order
  within that document assigned by the package rather than supplied by the author. *(US-1)*
- **FR-004**: A newly created version MUST be a draft: no legal standing, not in force, and
  invisible to readers. *(US-2)*
- **FR-005**: A draft MUST be freely editable and freely discardable. *(US-2)*
- **FR-006**: Publishing a draft MUST make it the version in force for its document, and MUST make
  the previously in-force version superseded. *(US-2)*
- **FR-007**: A document MUST have at most one version in force at any moment, and this MUST hold
  when two publishes are attempted against it concurrently. *(US-2)*
- **FR-008**: A document with no published version MUST be a valid state, reporting no version in
  force rather than failing. *(US-2, US-5)*
- **FR-009**: Publishing MUST be one-way. The package MUST offer no operation that returns a
  published version to draft, and none that makes a superseded version the one in force. *(US-2)*
- **FR-010**: Publishing a version that is already published MUST be refused, leaving the document
  unchanged. *(US-2)*
- **FR-011**: A published version's wording MUST NOT be changeable through any route the package
  offers, including ordinary use, shell sessions, management commands and data migrations the
  package ships. The rule MUST live with the data rather than with any one caller. *(US-3)*
- **FR-012**: An attempt to change a published version's wording MUST fail loudly rather than being
  silently discarded. *(US-3)*
- **FR-013**: A change of standing from in force to superseded MUST be the only change a published
  version ever undergoes. *(US-3)*
- **FR-014**: The package MUST offer no way to delete a published version, and no way to delete a
  document that has published versions. *(US-3)*
- **FR-015**: Publishing MUST produce the output a reader will be served at that moment, and store
  it alongside the source the author wrote. *(US-4)*
- **FR-016**: Stored output MUST never be produced again after publication, and MUST be unaffected
  by later changes to the markup rendering configuration. *(US-4)*
- **FR-017**: Producing the output MUST pass the authored markup through an allow list, so that
  content outside the allow list is absent from what is stored. *(US-4)*
- **FR-018**: Publication MUST be refused when the authored markup produces empty output. *(US-4)*
- **FR-019**: A draft MUST carry no stored output. *(US-4)*
- **FR-020**: Every version ever published MUST remain retrievable with its wording and its stored
  output intact, for as long as the data exists. *(US-5)*
- **FR-021**: The package MUST offer a way to ask a document for the version in force, for one
  named version, and for its published history in order. *(US-5)*
- **FR-022**: Drafts MUST be absent from a document's published history. *(US-5)*

### Key Entities

- **Document**: A named legal text with an identity that persists across rewordings, such as a
  privacy policy, a set of terms or a cookie policy. Holds no wording. Has a sequence of versions,
  of which at most one is in force.
- **Version**: One revision of a document, holding the markup its author wrote and, once published,
  the output a reader is served. Is a draft until published. Once published it is either the
  current one or superseded, and its wording never changes again.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Four documents run side by side, each accumulating its own version history, and no
  operation on any one of them alters any other.
- **SC-002**: After every publish, including two attempted concurrently against the same document,
  the document reports exactly one version in force.
- **SC-003**: Every route the package offers that could change a published version's wording is
  refused, with one test per route and no route left untested.
- **SC-004**: The output stored for a published version is identical when read after the markup
  rendering configuration has been changed.
- **SC-005**: A version published, superseded, and then retrieved returns its original wording and
  its original stored output, unchanged.
- **SC-006**: A document created and never published reports no version in force, and this is a
  normal answer rather than an error.
- **SC-007**: Restoring earlier wording is achieved only by publishing it as a new version, and the
  earlier version remains readable alongside it.

## Clarifications

### Session 2026-09-21

- **Q**: Can a document be retired or removed once it exists? → **A**: No. This feature offers no
  retirement, and a document with published versions cannot be deleted at all (FR-014). Retirement
  appears in no roadmap item, and adding it later would add to this model rather than change it.
- **Q**: Is a version's order assigned by the package or chosen by its author, and does a version
  carry a human-readable label such as "v2.1"? → **A**: The package assigns the order (FR-003). No
  author-supplied label in this feature. A label was considered and left out, because the existing
  packages in this space show what happens when an author-supplied number does not order anything.
- **Q**: Does publishing take effect immediately, or can it be dated for the future? → **A**:
  Immediately. Scheduled publication is not in this feature and not in the roadmap.
- **Q**: Can the version in force be rolled back to an earlier published version? → **A**: No.
  Restoring earlier wording means publishing it again as a new version (SC-007). A rollback would
  make publishing two-way, which contradicts FR-009.
- **Q**: Does this feature provide any admin, form, view or address? → **A**: No. Its whole surface
  is the model layer, exercised by tests. The authoring screens are issue #5 and the public pages
  are R2.

## Assumptions

- This feature ships no admin registration, no forms, no views and no URLs. Its consumers are the
  package's own later features and the host project's code.
- The version in force is whichever was published most recently. There is no way back to an earlier
  one.
- Publishing takes effect the moment it happens.
- Freezing applies to wording. A published version still moves from in force to superseded when the
  next one is published, and that is the only movement it ever has.
- A draft can be abandoned and discarded. Only what has been published is permanent.
- The package ships no list of document kinds. A site names its own documents, and nothing in the
  code knows that a privacy policy differs from a cookie policy.
- A document with no published version is a normal state rather than a defect.
- Whether a document is enforced is R5's decision and is absent here. Change summaries are R6 and
  translations are R7, both absent here.
