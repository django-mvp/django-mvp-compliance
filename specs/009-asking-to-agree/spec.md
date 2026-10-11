# Feature Specification: Asking a signed-in person to agree to what is outstanding

**Feature Branch**: `009-asking-to-agree`

**Created**: 2026-10-12

**Status**: Draft

**Serves**: G3, G5 · **Roadmap**: R4 · **Issue**: #86

**Input**: A site can publish its documents, record an acceptance and work out what a person still
has outstanding, but nothing ever asks anybody. A signed-in person who has not accepted the current
version of a document people agree to should be shown that version in full and asked to agree, on a
page that looks like the rest of the site. When they agree, the acceptance is recorded and they
carry on to wherever they were going. When more than one document is outstanding, they deal with
all of them in one sitting. If the record cannot be written, the person has not agreed, and they
are shown the page again. A person with nothing outstanding never sees any of this. A developer can
send a person to this page from their own code and have them returned to where they were headed.

## Scope

The package adds one page. It shows a signed-in user the current version of every document that is
outstanding for them, in full, and asks them to agree to each. One submission records an acceptance
of each version they agreed to. Once nothing is outstanding for them, they are sent on to the
address they were heading for.

The page decides whether to let a person through by reading the stored acceptances, and never from
what the person submitted. When a submission could not be recorded, the person stays on the page
and is told that nothing was recorded.

A developer sends a person to the page by its address, with the address to return them to. A person
who arrives with nothing outstanding is sent straight on and is shown nothing.

Some things stay out of this feature:

- Deciding when a person is sent to the page is R5 (#87): the check across a whole site, the
  addresses that stay reachable, the accounts that are let past, and whether an outstanding
  document stops a person at all. This feature stops nobody. It is a page a person is sent to, or
  opens, and can leave like any other page.
- What counts as outstanding is FS-003 and FS-007, and is unchanged: a document people agree to,
  with a version in force, whose current version the user has not accepted. A notice is never
  outstanding and never appears on the page.
- The acceptance itself is FS-003, and is unchanged: what it holds, that it is never edited, and
  that accepting the same version twice leaves one record.
- A summary of what changed since the version a person last accepted is R6.
- The document pages (FS-006) and the account area's list (FS-008) are unchanged. Neither gains a
  link to this page here.
- Refusing is not recorded. A person who does not agree leaves no record of any kind.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agreeing to an outstanding document and carrying on (Priority: P1)

A person signed up to a site and accepted its terms. The site has since published a new version.
While they are heading for their dashboard, the site sends them to the page that asks. They see the
new version of the terms in full, inside the site they were already using. They say they agree and
submit. The acceptance is recorded, and they arrive at the dashboard they were heading for.

**Why this priority**: It is the feature. Everything else in the package records and reports, and
this is the one place a person is asked.

**Independent Test**: Publish a document people agree to. Signed in as a user who has not accepted
its current version, open the page with a destination, check the stored wording of the current
version is on the page, submit agreement, and check that one acceptance of that version exists for
that user and that the response leads to the destination.

**Acceptance Scenarios**:

1. **Given** a signed-in user with one outstanding document, **When** they open the page, **Then**
   it shows that document's current version in full, as the wording stored at publication.
2. **Given** that page, **When** the user agrees and submits, **Then** an acceptance of the version
   they were shown is recorded for them, and they are sent to the address they were heading for.
3. **Given** a user who has opened the page and submitted nothing, **When** the records are read,
   **Then** no acceptance exists: opening the page records nothing.
4. **Given** a user on the page, **When** they submit without agreeing, **Then** nothing is
   recorded, and they are shown the page again and told what is still needed.
5. **Given** a visitor who is not signed in, **When** they request the page, **Then** they are sent
   to sign in, and after signing in they are back on the page with the same destination.
6. **Given** a user who accepted an earlier version of a document that now has a newer version in
   force, **When** they open the page, **Then** they are asked about the version in force, and
   agreeing adds a second acceptance and leaves the first as it was.
7. **Given** a notice, and a document people agree to with nothing published, **When** any user
   opens the page, **Then** neither is shown and neither can be agreed to there.
8. **Given** a user who agreed and was sent on, **When** they submit the same agreement again, for
   instance by going back in the browser, **Then** they still hold one acceptance of that version
   and are sent on as before.
9. **Given** a submission that names a version the user was not shown as outstanding, **When** it
   is processed, **Then** no acceptance of that version is recorded.

---

### User Story 2 - Being asked again when the record could not be written (Priority: P1)

A person reads the new terms, says they agree and submits. At that moment the site cannot store
the acceptance. They are not let through. They see the page again, are told that their agreement
was not recorded, and can submit again. Only when an acceptance is actually stored do they reach
the page they were heading for.

**Why this priority**: It is what makes the record worth relying on. A person who was let through
without an acceptance behind them is the one case the package exists to rule out, and it would
only ever show up later, when somebody asks for the evidence.

**Independent Test**: Make the write of an acceptance fail. Submit agreement, and check that the
response is the page and not the destination, that the person is told nothing was recorded, and
that no acceptance exists. Remove the failure, submit again, and check the acceptance exists and
the person is sent on.

**Acceptance Scenarios**:

1. **Given** a user who submits agreement while the acceptance cannot be stored, **When** the
   submission is processed, **Then** they are not sent to their destination, they are shown the
   page again, and they are told their agreement was not recorded.
2. **Given** that failure, **When** the records are read, **Then** the user holds no acceptance
   from that submission, and the document is still outstanding for them.
3. **Given** a user shown the page again after a failure, **When** they submit again and the
   acceptance is stored, **Then** they are sent to the destination they were first heading for.
4. **Given** a user who agreed to several documents in one submission, **When** storing any one of
   those acceptances fails, **Then** none of that submission's acceptances is kept, and all of
   those documents are still outstanding for them.
5. **Given** a submission that was processed without an error being raised, **When** the stored
   acceptances still leave something on the page outstanding, **Then** the user is shown the page
   again and is not sent on.
6. **Given** a failure, **When** the user is shown the page again, **Then** the response does not
   expose the cause to them, and the failure is reported to the project the way its other errors
   are.

---

### User Story 3 - Dealing with several outstanding documents in one sitting (Priority: P2)

A site publishes new versions of its terms and its privacy policy in the same week. A person who
signs in next is sent to the page once. Both documents are there, each readable in full, and each
with its own request to agree. They agree to both and submit once. Two acceptances are recorded,
one for each version, and they carry on.

**Why this priority**: Without it a person with three outstanding documents is sent round three
times, and each trip is a chance to give up. It depends on the first two stories and adds nothing
to what one acceptance means.

**Independent Test**: Leave three documents outstanding for one user. Open the page once and check
all three current versions are there. Agree to all three in one submission and check for three
acceptances and one redirect to the destination. Repeat, agreeing to two, and check for two
acceptances and the page again with the third.

**Acceptance Scenarios**:

1. **Given** a user with three outstanding documents, **When** they open the page, **Then** all
   three are on it, each with its current version readable in full, and each asked about
   separately.
2. **Given** that page, **When** the user agrees to all three and submits once, **Then** three
   acceptances are recorded, one per version, and they are sent to their destination.
3. **Given** that page, **When** the user agrees to two and submits, **Then** those two
   acceptances are recorded, and they are shown the page again with only the third document.
4. **Given** a user shown the page again with what remains, **When** they agree to it and submit,
   **Then** they are sent to the destination they were first heading for.
5. **Given** a user with several outstanding documents, **When** they open the page on separate
   occasions, **Then** the documents are in the same order each time, the order the document pages
   list them in.
6. **Given** a new version of one document is published after the user opened the page and before
   they submitted, **When** they submit agreement to everything they were shown, **Then** the
   documents whose versions are still in force are recorded, nothing is recorded for the version
   that was replaced, and they are shown the page again with the version now in force.
7. **Given** a document on the page stops being outstanding before the user submits, because they
   accepted it in another window or it was made a notice, **When** they submit, **Then** that
   document is passed over, the rest are recorded, and the submission is not treated as a failure.

---

### User Story 4 - Sending a person to the page from a project's own code (Priority: P2)

A developer has a checkout view that nobody should reach without having accepted the current
terms. In that view they send the person to the page, giving the checkout's address as the place to
come back to. A person with something outstanding is asked and then lands back on the checkout. A
person with nothing outstanding is sent straight back and never sees the page, so the developer
does not have to check first.

**Why this priority**: Until the check across a whole site exists (R5), this is the only way a
person reaches the page, and R5 itself is built on it.

**Independent Test**: From a view in a test project, redirect to the page with a destination. As a
user with something outstanding, follow it, agree, and check the final address is the destination.
As a user with nothing outstanding, follow it and check the response is a redirect to the
destination with no page shown. Repeat with a destination on another site and check it is not
followed.

**Acceptance Scenarios**:

1. **Given** a developer who sends a user to the page with a destination on the same site,
   **When** the user agrees to everything outstanding, **Then** they are sent to that destination.
2. **Given** a user with nothing outstanding, **When** they are sent to the page with a
   destination, **Then** they are sent on to it at once and are shown nothing.
3. **Given** a destination that points to another site, **When** the user would be sent on,
   **Then** it is not followed, and they are sent to the project's default destination.
4. **Given** no destination, **When** the user would be sent on, **Then** they are sent to the
   project's default destination.
5. **Given** a project that has set its own default destination, **When** a user is sent on with
   no usable destination, **Then** they arrive at the one the project set.
6. **Given** a destination that is the page itself, **When** the user would be sent on, **Then**
   they are sent to the default destination and are not sent round again.
7. **Given** a user who is sent to the page and has to be shown it more than once, after a failure
   or after agreeing to part of what is outstanding, **When** they finally have nothing
   outstanding, **Then** they are sent to the destination they were first given.
8. **Given** a developer reading the documentation, **When** they look for how to send a person to
   the page, **Then** it names the address, how the destination is given, and what happens to a
   person with nothing outstanding.

---

### User Story 5 - A page that belongs to the site, with nothing to write (Priority: P3)

A developer installs the package in a project built on django-mvp and mounts its pages. The page
that asks appears inside the project's own shell, with its theme and navigation, and the developer
has written no template for it. A developer who wants it arranged differently replaces the page's
template in their project, and the page still records and returns people as before.

**Why this priority**: A person asked to agree on a screen that looks like another application has
reason to distrust it. The guarantee is the developer's, though, and the page is usable before
anyone overrides anything.

**Independent Test**: In a project that mounts the package's pages and supplies no template of its
own, open the page and check it renders inside the project's shell. Add a template of the same
name to the project, open the page again, and check the project's template is the one used and
that agreeing still records an acceptance and returns the person.

**Acceptance Scenarios**:

1. **Given** a project that mounts the package's pages and has written no template for this one,
   **When** a user with something outstanding opens the page, **Then** it renders inside the
   project's shell.
2. **Given** a project that supplies its own template for the page, **When** a user opens the
   page, **Then** the project's template is used, and agreeing records and returns as before.
3. **Given** a project that does not mount the package's pages, **When** it starts and runs,
   **Then** nothing fails, and recording acceptances from code works as it did.
4. **Given** a compliance editor naming a new document, **When** they choose a slug that would
   give the document the page's address, **Then** the slug is refused.

---

### Edge Cases

- A person opens the page in two windows and agrees in both. The second submission finds nothing
  left to record, and they are sent on.
- A person's session ends while they are reading. On submitting they are sent to sign in, nothing
  is recorded, and they return to the page.
- A submission arrives from another site, made without the person's knowledge. It is refused, and
  no acceptance is recorded.
- A document is published for the first time while a person is on the page. It is not part of what
  they were shown, so their submission records nothing for it. If they would otherwise be sent on,
  they are shown the page again with it.
- A document on the page is made a notice before the person submits. It is passed over, and no
  acceptance of it is recorded.
- A project has turned on keeping the address a person connected from (FS-003). An acceptance
  recorded through the page carries it. With the setting off, it carries nothing extra.
- A person with nothing outstanding opens the page with no destination, perhaps from a bookmark.
  They are sent to the default destination.
- A staff user or superuser opens the page. They are asked like anybody else. Letting accounts
  past is R5.
- A person has ten documents outstanding. All ten are on the page, and the number of database
  queries is what it would be for one.
- A person leaves the page without agreeing. Nothing is recorded, and the documents stay
  outstanding.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST provide a page that shows a signed-in user every document that is
  outstanding for them, as FS-003 and FS-007 define outstanding, and no other document. *(US-1,
  US-3)*
- **FR-002**: For each document shown, the page MUST present its current version in full, serving
  the HTML stored at publication. *(US-1)*
- **FR-003**: The page MUST ask the user to agree to each document shown separately, and MUST take
  all of their answers in one submission. *(US-1, US-3)*
- **FR-004**: A submission MUST record one acceptance for each version the user agreed to, through
  the recording FS-003 provides, so that everything FS-003 guarantees about an acceptance holds
  for one recorded here. *(US-1, US-3)*
- **FR-005**: An acceptance MUST be recorded only for a version the user was shown on the page, and
  only while that version is still the current version of a document outstanding for them. A
  submission MUST NOT be able to record an acceptance of any other version. *(US-1, US-3)*
- **FR-006**: Opening the page MUST record nothing. Only a submission in which the user agreed
  records an acceptance, and a submission in which they agreed to nothing records none. *(US-1)*
- **FR-007**: A visitor who is not signed in MUST be sent to sign in and MUST be returned to the
  page afterwards with the destination they came with. *(US-1)*
- **FR-008**: After a submission, the user MUST be sent on only when the stored acceptances show
  that nothing is outstanding for them. The decision MUST be made from the stored records and
  never from the content of the submission. *(US-2)*
- **FR-009**: When an acceptance cannot be stored, the user MUST NOT be sent on. They MUST be
  shown the page again and told that their agreement was not recorded. *(US-2)*
- **FR-010**: The acceptances of one submission MUST be stored together or not at all. *(US-2,
  US-3)*
- **FR-011**: A failure to store MUST be reported to the host project the way its other errors
  are, and MUST NOT expose its cause to the user. *(US-2)*
- **FR-012**: When a user agrees to some of the documents shown and not others, the ones they
  agreed to MUST be recorded, and they MUST be shown the page again with those that remain.
  *(US-3)*
- **FR-013**: A document that is no longer outstanding for the user when their submission is
  processed MUST be passed over without failing the submission. *(US-3)*
- **FR-014**: Documents on the page MUST appear in the order the document pages list them in.
  *(US-3)*
- **FR-015**: The page MUST accept the address a user is to be returned to, and MUST keep it
  through every time the page is shown again and through signing in. *(US-1, US-4)*
- **FR-016**: A user MUST only ever be sent on to an address on the same site. A destination that
  is missing, points elsewhere, or is the page itself MUST be replaced by a default destination.
  *(US-4)*
- **FR-017**: The host project MUST be able to set the default destination, and the package MUST
  supply one that works when the project sets nothing. *(US-4)*
- **FR-018**: A signed-in user with nothing outstanding who requests the page MUST be sent on at
  once and MUST NOT be shown it. *(US-4)*
- **FR-019**: A submission MUST be refused unless it was made from the page by the signed-in user
  themselves. *(US-1)*
- **FR-020**: The page MUST render inside the host project's django-mvp shell without the project
  writing a template, and the project MUST be able to replace the page's template with its own.
  *(US-5)*
- **FR-021**: The page MUST be served with the package's other pages. A project that does not
  mount them MUST start, pass its system checks and behave as it did before. *(US-5)*
- **FR-022**: No document may take a slug that gives it the address of the page, and the page's
  address MUST never answer with a document. *(US-5)*
- **FR-023**: Showing the page and processing a submission MUST each cost a number of database
  queries that does not grow with the number of documents outstanding. *(US-3)*
- **FR-024**: The feature MUST stop nobody from leaving the page, and MUST record nothing about a
  user who does not agree. *(US-1)*
- **FR-025**: Every user-facing string this feature adds MUST be translatable, and none may state
  or imply that the person or the site is compliant. *(US-1, US-2)*
- **FR-026**: The documentation MUST explain how a developer sends a person to the page and has
  them returned, what a person with nothing outstanding experiences, what happens when an
  acceptance cannot be stored, how the default destination is set, and how the page's template is
  replaced. *(US-4, US-5)*

### Key Entities

- **Acceptance** (FS-003): unchanged. This feature is the first thing in the package that records
  one on a person's own action. It records through FS-003 and adds no field.
- **Version** (FS-001, FS-006): unchanged, and read only. The page serves the current version's
  stored HTML, and an acceptance recorded here points at the version that was shown.
- **Document** (FS-001, FS-007): unchanged, apart from one more slug that cannot be taken. Whether
  a document is outstanding for a user is answered as FS-003 answers it.
- **Destination**: the address a user is returned to once nothing is outstanding. It travels with
  the request and is not stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every user sent on from the page holds an acceptance of the current version of every
  document that was outstanding for them when they arrived. No user is sent on without one.
- **SC-002**: When storing an acceptance fails, the user is shown the page again every time, and
  no acceptance from that submission exists.
- **SC-003**: Every acceptance recorded through the page points at a version whose wording was on
  the page the user submitted from.
- **SC-004**: A user with several outstanding documents clears all of them with one submission and
  is redirected once.
- **SC-005**: A user who agrees to everything arrives at the address they were heading for when
  they were sent to the page, including after a failed attempt.
- **SC-006**: A user with nothing outstanding who is sent to the page reaches their destination
  without the page being shown.
- **SC-007**: No user is ever sent from the page to an address on another site.
- **SC-008**: A project that mounts the package's pages gets the page, inside its own shell, with
  no template written and no setting changed.
- **SC-009**: The number of database queries to show the page is the same for a user with one
  outstanding document as for a user with ten.

## Clarifications

### Session 2026-10-12

- **Q**: When several documents are outstanding, does a person agree to them with one answer, or
  to each one separately? → **A**: Separately, in one submission (FR-003). An acceptance is the
  record that a person agreed to one version of one document, and an answer that covers three
  documents at once is weaker evidence for each of them. One submission still keeps it to a single
  sitting.
- **Q**: What happens when a person agrees to some of the documents shown and not the rest? →
  **A**: What they agreed to is recorded, and the page comes back with what remains (FR-012).
  Discarding an agreement a person gave because they withheld another would leave the record
  saying less than what happened.
- **Q**: If storing one of several acceptances fails, are the others kept? → **A**: No. One
  submission's acceptances are stored together or not at all (FR-010). The person can then be told
  one true thing, that nothing was recorded, and submitting again is harmless because FS-003 keeps
  one record per person and version.
- **Q**: A new version is published while a person is reading the old one. Which is recorded? →
  **A**: Neither (FR-005). They never saw the new one, so an acceptance of it would be false. The
  old one is no longer in force, so recording it would not settle anything and they would be asked
  again regardless. They are shown the page again with the version now in force.
- **Q**: Where does a person go when no destination was given, or the one given cannot be used? →
  **A**: To a default the project can set, with one supplied by the package that works when
  nothing is set (FR-016, FR-017). A destination on another site is never followed, because the
  address could be written by anybody who builds a link to the page.

## Assumptions

- FS-001 to FS-008 are delivered, and this spec is written against them as they stand on main:
  acceptances are recorded from code, what is outstanding for a person is answered in one query,
  each published version has a page, and a document is either one people agree to or a notice.
- The page asks about every document that is outstanding for the person. R5 decides which
  outstanding documents stop a person and may narrow what a person has to clear before they are
  sent on. Until then all outstanding documents are treated alike.
- R5 sends people to this page the same way a developer does, by its address with a destination,
  and relies on a person with nothing outstanding being sent straight on.
- The host project is built on django-mvp and has a sign-in page, as the account area's list
  (FS-008) already assumes.
- Nothing links to the page from the package's other pages. Until R5 is delivered, a person
  reaches it because the project's own code sent them there.
- An acceptance recorded here holds what FS-003 says an acceptance holds, including the optional
  connecting address when the project has turned that on. No new personal data is stored, so
  Article XIV asks for nothing further.
- "Outstanding" is used here as CONTEXT.md already uses it under *Notice* and *Enforcement*. It
  has no entry of its own in the glossary, and one should be added when this feature is built.
- How the page is laid out is settled on a prototype reviewed on screen before the implementation
  is planned: how several documents are arranged, where the request to agree sits beside a long
  document, and how a failure is announced. No requirement here fixes wording or appearance.
