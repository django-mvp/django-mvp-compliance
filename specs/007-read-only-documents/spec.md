# Feature Specification: Documents that are read but never agreed to

**Feature Branch**: `007-read-only-documents`

**Created**: 2026-09-29

**Status**: Draft

**Serves**: G3, G6 · **Roadmap**: R5 · **Issue**: #65

**Input**: Not every legal document a site publishes is something a person agrees to. A privacy
policy or terms of use is accepted by each user, and that acceptance is recorded. An impressum, the
legal notice a German site must publish, is only there to be read: nobody agrees to it, and nobody
should ever be asked to. Right now the package treats every document with a version in force as one
a signed-in user still has to accept, so publishing an impressum would leave every user with
something outstanding that they can never sensibly clear. A document should say which kind it is.

## Scope

Each document is one of two kinds:

- **A document people agree to**, such as a privacy policy or terms of use. It behaves exactly as it
  does today. When a version of it is in force and a user has not accepted that version, the
  document counts towards what the user still has to accept.
- **A notice**, such as an impressum. It is only there to be read. It is published, versioned and
  served at its own address like any other document. It never counts towards what anybody still has
  to accept, no acceptance of it can be recorded, and its page never says that the reader agreed to
  it.

The kind belongs to the document, not to a version. A document is one people agree to unless it is
made a notice. The kind can be changed at any time, and changing it never touches an acceptance that
has already been recorded.

A project links to a notice from its own templates, usually the footer, through the document's
address, in the same way it links to any other document.

Some things stay out of this feature:

- Deciding per document whether agreement is enforced, so that a document people agree to may still
  never stop anybody, is a separate R5 item. A notice is never outstanding, so no enforcement can
  ever apply to it.
- Applying the check across the whole site is the rest of R5.
- The list of what a person has agreed to, in their account area, is issue #66. Notices are left out
  of it because nobody can have agreed to one, and this feature is what lets that list tell the two
  kinds apart.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publishing a notice nobody is asked to accept (Priority: P1)

A site operator in Germany has to publish an impressum. They create a document for it, make it a
notice, write it and publish it. It gets a version number and a page at its own address, and the
project links to it from the footer. Signed-in users are never counted as owing anything for it:
what they still have to accept is exactly what it was before the impressum existed. Nothing can
record that a user accepted it, and its page reads the same for everyone.

**Why this priority**: It is the feature. Without it, publishing an impressum leaves every user with
something outstanding that they can never sensibly clear, and a site that needs one cannot use the
package for it.

**Independent Test**: In the demo, create a document, make it a notice and publish a version. Confirm
that a signed-in user with no acceptances has the same documents outstanding as before it was
published, that recording an acceptance of the notice's version is refused, and that its page shows
the version's wording at its address with no statement of agreement.

**Acceptance Scenarios**:

1. **Given** a notice with a version in force and a signed-in user, **When** the documents the user
   still has to accept are worked out, **Then** the notice is not among them.
2. **Given** a notice with a version in force, **When** anybody asks whether the notice is
   outstanding for a given user, **Then** the answer is no.
3. **Given** a notice's published version, **When** anything tries to record a user's acceptance of
   it, **Then** it is refused and no acceptance is created.
4. **Given** a notice with a version in force, **When** a visitor, signed in or not, opens its
   address, **Then** the page shows that version's stored wording, with its number and the date it
   came into force, in the same way as for any other document.
5. **Given** a notice's page, **When** a signed-in user opens it, **Then** the page carries no
   statement that the user agreed to it.
6. **Given** a notice with several published versions, **When** its page is opened with `?version=`
   and the number of an earlier one, **Then** that version's stored wording is shown, as for any
   other document.
7. **Given** a document created without anyone choosing its kind, **When** a version of it is in
   force, **Then** it counts towards what a user who has not accepted that version still has to
   accept, exactly as documents do today.
8. **Given** a site with notices and documents people agree to, **When** a document's page is
   opened, **Then** the list of documents beside the wording includes both kinds.

---

### User Story 2 - Seeing and changing which kind a document is (Priority: P2)

A member of staff looking over the site's documents in the admin can see at a glance which are
notices, so a misconfigured impressum is spotted without opening each document. The kind can be
chosen when a document is created and changed afterwards. A cookie policy first set up as a notice
and later made something people agree to becomes outstanding for every user who has not accepted
its version in force. A document people agree to that is later made a notice stops being asked
about, and every acceptance of it already recorded stays exactly as it was.

**Why this priority**: US-1 works with the kind set once at creation. This covers the operator
getting it wrong or the site's needs changing, and makes the setting visible where staff manage
documents.

**Independent Test**: In the demo, record a user's acceptance of a document's version in force, then
make the document a notice. Confirm the acceptance is unchanged and still produced in everything
held about that user, and that the document is no longer outstanding for a user who never accepted
it. Make it a document people agree to again and confirm it is outstanding for that user once more.

**Acceptance Scenarios**:

1. **Given** the admin's list of documents, **When** it is read, **Then** it shows each document's
   kind.
2. **Given** a new document being created in the admin, **When** it is saved, **Then** its kind is
   the one chosen, or a document people agree to when nobody chose.
3. **Given** a document with published versions, **When** its kind is changed, through the admin or
   from code, **Then** the change is saved and no version of it changes.
4. **Given** a document people agree to, with recorded acceptances, **When** it is made a notice,
   **Then** every one of those acceptances still exists, unchanged, and still appears in everything
   held about the person it names.
5. **Given** a document people agree to that has just been made a notice, **When** the documents a
   user who never accepted it still has to accept are worked out, **Then** it is not among them.
6. **Given** a notice made into a document people agree to, **When** the documents a user still has
   to accept are worked out, **Then** it is among them unless that user has accepted its version in
   force.

---

### Edge Cases

- A notice has only drafts. Its address answers "not found", as for any other document, and it is
  outstanding for nobody.
- A document people agree to was made a notice after a user accepted its version in force. The
  notice's page still carries no statement of agreement for that user. The acceptance itself is
  unchanged and is produced with everything else held about them.
- A notice was made into a document people agree to. Acceptances recorded before it became a notice
  count again, so a user who had accepted the version still in force has nothing outstanding for it.
- Recording the same user's acceptance of a notice twice, or from two requests at once, is refused
  both times and creates nothing.
- A version of a notice is published. The announcement to the people running the site goes out as
  for any other document, since it is addressed to them and not to the site's users.
- A future per-document enforcement setting is set on a notice. Nothing can be enforced, because a
  notice is never outstanding.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each document MUST be one of two kinds: a document people agree to, or a notice.
  *(US-1, US-2)*
- **FR-002**: A document whose kind nobody chose MUST be a document people agree to. *(US-1, US-2)*
- **FR-003**: A notice MUST never be counted among the documents a user still has to accept, by any
  route that answers that question, for many documents or for one. *(US-1, US-2)*
- **FR-004**: Recording an acceptance of any version of a notice MUST be refused, by every route
  that records an acceptance, and MUST create nothing. *(US-1)*
- **FR-005**: A notice MUST be published, numbered, served at its address and listed among the
  documents on every document page in the same way as a document people agree to. *(US-1)*
- **FR-006**: A notice's page, for its current or an earlier version, MUST NOT state that the
  signed-in reader agreed to it. *(US-1)*
- **FR-007**: A document's kind MUST be changeable at any time, from the admin and from code, and
  changing it MUST NOT change any version or any recorded acceptance. *(US-2)*
- **FR-008**: Once a document people agree to is made a notice, FR-003 and FR-006 MUST apply to it
  immediately. Once a notice is made a document people agree to, it MUST be counted among the
  documents a user still has to accept unless the user has accepted its version in force. *(US-2)*
- **FR-009**: The admin's list of documents MUST show each document's kind, and the admin MUST let
  the kind be chosen when a document is created and changed afterwards. *(US-2)*
- **FR-010**: Working out what a user still has to accept MUST still cost a number of database
  queries that does not grow with the number of documents. *(US-1)*
- **FR-011**: Upgrading an existing installation MUST leave every existing document a document people
  agree to, and MUST NOT drop or change any version or acceptance. *(US-1, US-2)*
- **FR-012**: Every user-facing string this feature adds MUST be translatable. *(US-1, US-2)*
- **FR-013**: The documentation MUST explain the two kinds, how to make a document a notice, and what
  a notice is never part of. *(US-1, US-2)*
- **FR-014**: The glossary MUST define *Notice* as a document that is published to be read and is
  never accepted, such as an impressum. *(US-1)*

### Key Entities

- **Document** (FS-001, FS-006): gains its kind, either a document people agree to or a notice. The
  kind is not frozen by publication.
- **Version** (FS-001, FS-002): unchanged. A notice's versions are numbered, published and superseded
  like any other.
- **Acceptance** (FS-003): unchanged, and never created for a notice's version. Acceptances recorded
  before a document became a notice are kept as they are.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With any number of notices in force, the documents a user still has to accept are
  exactly the documents people agree to whose version in force that user has not accepted.
- **SC-002**: No route in the package creates an acceptance of a notice's version.
- **SC-003**: Changing a document's kind, in either direction, leaves the count and content of
  versions and acceptances unchanged.
- **SC-004**: The number of database queries for working out what a user still has to accept is the
  same with one document as with fifty.
- **SC-005**: After upgrading, every document that existed before behaves exactly as it did.
- **SC-006**: A developer can publish an impressum and link to it from the site's footer with no
  more work than any other document takes, apart from choosing its kind.

## Clarifications

### Session 2026-09-29

- **Q**: Does the kind belong to the document or to each version? → **A**: The document (FR-001).
  Whether people agree to a text depends on what the text is for, not on one wording of it. A kind
  per version would let a document's page switch between asking and not asking with each rewording,
  and "still has to accept" would have to be answered version by version.
- **Q**: What kind is a document when nobody chooses? → **A**: A document people agree to (FR-002).
  That is how every document behaves today, so nothing changes for a site that never uses notices.
  The documents most sites publish first, a privacy policy and terms, are agreed to.
- **Q**: Is the kind frozen once a version is published, like the slug? → **A**: No (FR-007). The slug
  is frozen because links depend on it. Nothing depends on the kind except the question of who still
  has to accept, which is about the future. Acceptances already recorded are never touched, so
  correcting the kind loses no evidence. A kind that could never be corrected would leave a
  misconfigured impressum outstanding for every user for good.
- **Q**: What happens to acceptances of a document that is later made a notice? → **A**: They are
  kept exactly as they are and are still produced with everything held about the person (FR-007,
  US-2 scenario 4). An acceptance is a historical fact. The document's page stops saying the reader
  agreed, because the page describes the document as it now stands (FR-006), but the record is
  unchanged.
- **Q**: Is recording an acceptance of a notice ignored or refused? → **A**: Refused (FR-004), in the
  same way recording against an unpublished version is refused. Silently doing nothing would hide a
  project's bug, and creating the record would put a false statement into the evidence.

## Assumptions

- FS-001 to FS-006 are delivered, and this spec is written against them as they stand on main: the
  documents a user still has to accept are worked out in one query, acceptances can be recorded from
  code, and each document has a page at its address.
- The flow that asks a user to accept documents (R4) and the site-wide check (R5) are not built yet.
  Both will read what a user still has to accept, so leaving notices out of that answer covers them
  without further work.
- The announcement email from FS-005 goes to the people running the site, so it is sent for a
  notice's new version as for any other.
- The kind is not personal data, so Article XIV does not apply.
