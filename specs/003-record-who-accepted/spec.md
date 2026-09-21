# Feature Specification: The record of who accepted which version

**Feature Branch**: `003-record-who-accepted`

**Created**: 2026-09-21

**Status**: Draft

**Serves**: G2 · **Roadmap**: R3 · **Issue**: #20

**Input**: A site that publishes a document needs to know, later and reliably, who agreed to it.
That means a record naming the person, the exact version they agreed to, and when. Not the
document: "agreed to the privacy policy" is not evidence of anything on its own. The record is a
statement about something that happened, so nothing afterwards revises it. Someone who agrees to a
newer version gains a second record and keeps the first, because both are true.

## Scope

An acceptance is the record that one user agreed to one published version of one document, at one
moment. This feature is where that fact gets written, where it stays written, and where it can be
asked about.

It is the rules, not the screens. This feature adds no forms, no pages and no addresses. The flow
that shows a person a document and collects their answer is R4, and this is what that flow writes
into. Deciding where across a site a person meets that flow is R5. Producing everything held about
one person, alongside the wording they were shown, is issue #21. Erasing a person's records on
request is issue #22. The account-area view is R9 and the site-wide picture is R10.

Cookie choices are not acceptances and are absent here. They belong to a visitor rather than a
user, and a visitor may change them, which is the opposite of everything below. They are R8.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One acceptance, written down and left alone (Priority: P1)

A person agrees to a published version of a document, and that produces a record naming who they
are, which version it was, and when it happened. From that moment the record is finished. Nothing
in the package will edit it, and nothing in the package will delete it.

The record points at a version and never at a document, because a document has said different
things at different times and a record naming only the document cannot say which of them the
person saw.

**Why this priority**: It is the feature. Every other story here, and R4, R5, R9 and R10, either
writes one of these or reads one.

**Independent Test**: Record an acceptance, confirm it names the person, the version and the time,
then attempt to change it and to delete it through every route the package offers and confirm each
attempt fails and leaves the record as it was.

**Acceptance Scenarios**:

1. **Given** a user and a published version, **When** the user's acceptance of it is recorded,
   **Then** a record exists naming that user, that version and the moment it happened.
2. **Given** an acceptance, **When** any part of it is changed and saved, **Then** the attempt
   fails with an error and the stored record is unchanged.
3. **Given** an acceptance, **When** the change is attempted outside ordinary use, from a shell or
   a management command or a data migration the package ships, **Then** it fails the same way,
   because the rule lives with the data and not with any one caller.
4. **Given** an acceptance, **When** deletion of it is attempted, **Then** the package offers no
   way to do it.
5. **Given** a version that has never been published, **When** an acceptance of it is attempted,
   **Then** it is refused, because a draft has no standing for anybody to agree to.
6. **Given** a document rather than one of its versions, **When** an acceptance of it is attempted,
   **Then** there is no way to express that, because acceptance is of a version.
7. **Given** an acceptance of a version that is later superseded, **When** the record is read
   afterwards, **Then** it still points at the version the person actually saw.

---

### User Story 2 - A later version is a second record, not an update (Priority: P1)

A document gets reworded and a person agrees to the new wording. They agreed to the old wording
too, and that happened, so they now have two records rather than one that has moved. Both stand for
as long as the data exists.

Agreeing twice to the *same* version is different. A person who submits the same form twice has not
done two things, so the second attempt leaves them with the one record they already had.

**Why this priority**: This is the difference between a record and a status field. A site that
overwrites the old row when somebody accepts a new version cannot answer the only question anybody
ever asks it, which is what this person agreed to at the time of the thing being disputed.

**Independent Test**: Publish two versions of one document, record the same person's acceptance of
each in turn, confirm both records exist and the first is untouched, then repeat one of them and
confirm no third record appears.

**Acceptance Scenarios**:

1. **Given** a person with an acceptance of one version, **When** they accept a later version of
   the same document, **Then** they have two records and the earlier one is unchanged.
2. **Given** a person with acceptances of several versions, **When** their acceptances are listed,
   **Then** every one of them is present, in the order they happened.
3. **Given** a person who has already accepted a version, **When** their acceptance of that same
   version is recorded again, **Then** they still have exactly one record of it.
4. **Given** two people, **When** each accepts the same version, **Then** each has their own record
   and neither can be mistaken for the other.
5. **Given** two attempts to record the same person's acceptance of the same version at the same
   moment, **When** both complete, **Then** exactly one record exists.

---

### User Story 3 - Asking what a person still owes (Priority: P1)

Something has to be able to ask whether a given person has accepted what is currently in force, and
which documents they have outstanding. Without that the record is written and never read, and the
flow in R4 has no question to put to it.

The answer is a plain statement about the record: this person has accepted the version in force for
this document, or they have not. What anybody does about the answer belongs to R4 and R5.

**Why this priority**: R4 and R5 cannot begin without it, and it is the only part of this feature
that anything outside the package calls on an ordinary page request.

**Independent Test**: Give one person acceptances of some documents and not others, then ask what
they have outstanding and confirm the answer names exactly the documents whose version in force
they have not accepted.

**Acceptance Scenarios**:

1. **Given** a person who has accepted the version in force for a document, **When** that document
   is asked about for them, **Then** the answer is that nothing is outstanding.
2. **Given** a person who has never accepted anything for a document that has a version in force,
   **When** that document is asked about for them, **Then** it is outstanding for them.
3. **Given** a person who accepted a version that has since been superseded, **When** that document
   is asked about for them, **Then** it is outstanding, because what is in force is not what they
   accepted.
4. **Given** a person and several documents, **When** they are asked what they have outstanding,
   **Then** the answer names every document whose version in force they have not accepted, and no
   others.
5. **Given** a document with no published version, **When** it is asked about for any person,
   **Then** nothing is outstanding, because there is nothing in force to accept.
6. **Given** a person with nothing outstanding anywhere, **When** they are asked, **Then** the
   answer is empty and this is a normal result rather than an error.
7. **Given** a site running many documents, **When** one person is asked what they have
   outstanding, **Then** the answer is produced without consulting each document separately.

---

### User Story 4 - Records outlive the accounts they name (Priority: P2)

Accounts get closed and tidied up, and that is an ordinary administrative act rather than a
statement about the evidence. By default an acceptance survives the removal of the account it
names, because it is a record of something that happened and the package exists to stop such a
record going missing quietly.

Some sites mean the opposite, and they are not wrong. A closed account leaving personal data behind
indefinitely is exactly what data minimisation is pointed at. So this is a setting the host project
controls, and the package's own default is that the records stay.

A surviving record still has to say who it was about. A record that outlives its account and can no
longer name the person it belongs to is not evidence of anything.

**Why this priority**: It is a decision that becomes expensive to reverse once real records exist,
so it belongs in this feature rather than a later one. P2 rather than P1 because the three stories
above are what make the record exist and be readable, and this governs what happens to it much
later.

**Independent Test**: Record acceptances for a person, remove their account under each setting, and
confirm that the default leaves the records in place and still able to name whose they are, while
the other setting leaves none of them.

**Acceptance Scenarios**:

1. **Given** a person with acceptances and the package's default setting, **When** their account is
   removed, **Then** their acceptances are still there.
2. **Given** a surviving acceptance whose account is gone, **When** it is read, **Then** it still
   identifies the person it is about and still points at the version they accepted.
3. **Given** a surviving acceptance whose account is gone, **When** everything held about that
   person is asked for, **Then** their records are found together rather than scattered
   unreachably.
4. **Given** a person with acceptances and the setting changed to remove them, **When** their
   account is removed, **Then** none of their acceptances remain.
5. **Given** either setting, **When** an account is removed, **Then** no other person's records are
   affected.

---

### User Story 5 - Nothing held about a person that the site did not ask for (Priority: P2)

The record holds three things: the person, the version, the time. A site can decide to hold more,
because noting where a request came from makes the record harder to dispute and some sites need
that. It is personal data about somebody who did not ask for it to be kept, so the package holds
none of it unless the project says so.

**Why this priority**: Adding it later is a change to what is held about every person who has
already accepted something, and the constitution treats widening that as a deliberate act rather
than a routine one. P2 because the record works without it.

**Independent Test**: Record an acceptance with the package's defaults and confirm nothing beyond
the three facts is held, then turn the additional evidence on, record another, and confirm it is
held for that one and still absent from the first.

**Acceptance Scenarios**:

1. **Given** the package's defaults, **When** an acceptance is recorded, **Then** nothing is held
   about the person beyond who they are, which version, and when.
2. **Given** a project that has turned the additional evidence on, **When** an acceptance is
   recorded, **Then** it is held alongside the three facts.
3. **Given** records made before the additional evidence was turned on, **When** they are read
   afterwards, **Then** they are unchanged and hold none of it.
4. **Given** a project that turns the additional evidence off again, **When** records made while it
   was on are read, **Then** they still hold what was held at the time, because an acceptance is
   never edited.

---

### Edge Cases

- A version is published between a person being shown a document and their answer arriving. Their
  acceptance is recorded against the version they actually read, which is now superseded, and that
  document is outstanding for them again.
- Somebody submits the same agreement twice in quick succession. They end with one record.
- A document has never published anything. Nobody has it outstanding and nobody can accept it.
- An account is removed and later recreated with the same name. The new account is a different
  person as far as the record is concerned, and inherits nothing.
- A person accepts a version, the document is reworded several times afterwards, and they never
  return. Their record still points where it pointed and the document is outstanding for them.
- A site asks what one person has outstanding on a page that runs on every request. The question
  has to be cheap enough to live there.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An acceptance MUST record the user, the version they accepted, and the moment it
  happened. *(US-1)*
- **FR-002**: An acceptance MUST point at a version and MUST NOT be expressible against a document.
  *(US-1)*
- **FR-003**: An acceptance MUST only be recordable against a published version, whether that
  version is in force or superseded. A version that has never been published MUST be refused.
  *(US-1)*
- **FR-004**: An acceptance MUST NOT be changeable through any route the package offers, including
  ordinary use, shell sessions, management commands and data migrations the package ships. The rule
  MUST live with the data rather than with any one caller. *(US-1)*
- **FR-005**: An attempt to change an acceptance MUST fail loudly rather than being silently
  discarded. *(US-1)*
- **FR-006**: The package MUST offer no operation that deletes an acceptance, apart from the
  account-removal setting in FR-013 and the erasure path in issue #22. *(US-1)*
- **FR-007**: An acceptance MUST continue to point at the version it was recorded against after
  that version is superseded. *(US-1)*
- **FR-008**: Accepting a later version of a document MUST create a second acceptance and MUST
  leave every earlier one unchanged. *(US-2)*
- **FR-009**: A user MUST hold at most one acceptance of any given version. Recording the same
  user's acceptance of the same version again MUST leave them with the one record they already had,
  and MUST NOT fail. *(US-2)*
- **FR-010**: FR-009 MUST hold when two such attempts are made concurrently. *(US-2)*
- **FR-011**: The package MUST be able to answer, for one user and one document, whether the
  version in force has been accepted. *(US-3)*
- **FR-012**: The package MUST be able to answer, for one user, which documents have a version in
  force that the user has not accepted. A document with no version in force MUST NOT appear in that
  answer. *(US-3)*
- **FR-013**: The package MUST offer a setting that decides whether a user's acceptances survive
  the removal of their account, defaulting to surviving. *(US-4)*
- **FR-014**: An acceptance that survives the removal of its account MUST still identify the person
  it is about, and MUST still be retrievable together with that person's other acceptances. *(US-4)*
- **FR-015**: Removing one account MUST NOT affect any other person's acceptances, under either
  setting. *(US-4)*
- **FR-016**: The package MUST hold nothing about a person beyond the three facts in FR-001 unless
  the host project turns additional evidence on. *(US-5)*
- **FR-017**: Turning additional evidence on or off MUST affect only acceptances recorded
  afterwards, and MUST leave existing records untouched. *(US-5)*
- **FR-018**: Answering FR-011 and FR-012 MUST be cheap enough to run on an ordinary page request,
  and MUST NOT cost a separate lookup per document. *(US-3)*

### Key Entities

- **Acceptance**: The record that one user agreed to one published version of one document, at one
  moment. Never edited. Removed only by the erasure path in issue #22, or by the account-removal
  setting in FR-013 when a project has chosen it.

*Document* and *Version* are defined by FS-001 and are unchanged here.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every route the package offers that could change or delete an acceptance is refused,
  with one test per route and no route left untested.
- **SC-002**: A person who accepts three successive versions of one document ends with three
  records, and the first two are exactly what they were when written.
- **SC-003**: The same acceptance submitted twice, including twice at once, leaves exactly one
  record.
- **SC-004**: For a person with a mix of accepted, superseded and never-accepted documents, the
  outstanding answer names exactly the documents whose version in force they have not accepted.
- **SC-005**: Asking what one person has outstanding across any number of documents costs a fixed
  number of lookups rather than one per document.
- **SC-006**: With the package's default setting, removing an account leaves that person's
  acceptances in place, still naming whose they are and still retrievable as a set.
- **SC-007**: With the setting changed, removing an account leaves none of that person's
  acceptances, and every other person's are untouched.
- **SC-008**: An acceptance recorded under the package's defaults holds the person, the version and
  the time, and nothing else.

## Clarifications

### Session 2026-09-21

- **Q**: Can an acceptance be recorded against a superseded version, or only against the version in
  force? → **A**: Any published version, in force or superseded (FR-003). A version can be
  published between a person reading a document and their answer arriving, and recording what they
  actually read is the honest answer. Restricting to the version in force would either lose that
  acceptance or record them as having agreed to wording they never saw. What is *outstanding* is
  still measured against the version in force (FR-012), so that person is asked again.
- **Q**: Is "outstanding" measured across every document, or only the ones a site enforces?
  → **A**: Every document with a version in force (FR-012). Which documents are enforced is R5's
  decision, and the record layer must not carry an enforcement policy it does not own. R5 filters
  the answer this feature gives.
- **Q**: Recording the same person's acceptance of the same version twice: a second record, or an
  error? → **A**: Neither. It succeeds and leaves one record (FR-009). A repeated submission is an
  interface accident rather than a second thing that happened, and failing would break the flow in
  R4 for a person who did nothing wrong.
- **Q**: When records survive a removed account, what identifies the person they are about?
  → **A**: The record has to answer that on its own (FR-014), and a person's surviving records have
  to be findable together, because issue #21 has to produce them and issue #22 has to erase them.
  How that is held is a design decision for the implementation rather than a decision here.
- **Q**: When a project has chosen to remove acceptances along with the account, does that removal
  need the audit trail that erasure on request carries? → **A**: No. It is a behaviour the project
  configured in advance rather than an act about one named person. The audited path, and what its
  trace may hold, is issue #22's problem.

## Assumptions

- This feature ships no forms, no views and no URLs. Its consumers are the package's own later
  features and the host project's code.
- An acceptance belongs to a signed-in user. There is no such thing as an acceptance by a visitor
  who is not signed in, and nothing here records one.
- Acceptances are never withdrawn. A person who changes their mind about a document does not have
  their record altered, because agreeing to it is a thing that happened. Cookie choices are
  withdrawable and are R8.
- What a person was shown is the stored output FS-001 fixes at publication. This feature points at
  the version and holds no copy of the wording.
- Translations do not change what an acceptance points at. R7 adds readings of a version, and the
  canonical text is what was accepted.
- Additional evidence beyond the three facts means something like where a request came from.
  Deciding exactly which are offered is a design decision, bounded by the constitution's rule that
  each one is justified where it is defined.
- Bringing in acceptances from a system a site used before this package is out of scope here and is
  covered by no roadmap item. It was raised at intake as a possible gap rather than folded in.
- FS-001 is specified and not yet delivered. This spec is written against its specification.
