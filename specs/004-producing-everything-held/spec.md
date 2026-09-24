# Feature Specification: Producing everything held about one person's acceptances

**Feature Branch**: `004-producing-everything-held`

**Created**: 2026-09-21

**Status**: Draft

**Serves**: G2 · **Roadmap**: R3 · **Issue**: #21

**Input**: The record earns its keep the day somebody asks for it, and that day is usually a
complaint, a dispute, or a regulator with a deadline. Whoever runs the site needs to be able to
answer: this is what the person accepted, this is when, and this is the exact wording they were
shown at the time. The wording is the part that is easy to get wrong. A line saying someone
accepted the third version on a date is not an answer on its own.

## Scope

For one named person, this produces everything the package holds about them, in a form somebody can
be handed. Today that is their acceptances, each with the document, the version, the moment it
happened, and the wording served at the time. It is the package's single answer about a person
rather than a report about one kind of record, so the cookie choices in R8 join it later without
the surface changing.

It is produced by somebody fielding a request, on behalf of a person, one person at a time. The
signed-in person's own view of what they have agreed to is R9: the same facts, a different audience
and a different surface. The site-wide picture of who has accepted what is R10. Erasing a person's
records is issue #22.

It answers for what this package holds and for nothing else. It offers no way for a host project to
attach data from its own models, which is R11, and it never presents itself as a complete answer to
a request that reaches beyond consent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Everything held about one person, in one answer (Priority: P1)

Somebody is fielding a request about a named person and needs what the package holds about them.
Not a search they have to assemble, and not one query per document: one answer, covering every
acceptance held for that person, each naming the document, which version it was, and when it
happened.

A person the package holds nothing about is an answer too, and an important one. The requester
needs to be able to say that definitely, rather than reading an empty screen and wondering whether
they asked the question correctly.

**Why this priority**: It is the feature. Without it the record is held and cannot be produced,
which leaves G2 half met.

**Independent Test**: Give one person acceptances across several documents, produce the answer, and
confirm it contains every one of them with its document, version and time, and nothing belonging to
anybody else. Then produce it for a person with no records and confirm the answer says so.

**Acceptance Scenarios**:

1. **Given** a person with acceptances across several documents, **When** the answer is produced
   for them, **Then** it contains every acceptance held for that person.
2. **Given** such an answer, **When** each entry is read, **Then** it names the document, the
   version accepted, and the moment it happened.
3. **Given** several people with acceptances, **When** the answer is produced for one of them,
   **Then** it contains nothing belonging to anybody else.
4. **Given** a person with several acceptances of one document over time, **When** the answer is
   produced, **Then** every one of them appears rather than only the most recent.
5. **Given** a person the package holds nothing about, **When** the answer is produced, **Then** it
   states that nothing is held, and this is a normal result rather than an error or an empty
   screen.
6. **Given** the same person and no change to the records, **When** the answer is produced twice,
   **Then** both answers say the same thing.

---

### User Story 2 - The wording they were shown, alongside each record (Priority: P1)

An entry saying somebody accepted the third version of the privacy policy on a date in March is not
an answer. What the third version said is the answer, and it has to be the wording that was served
to them rather than anything produced later.

**Why this priority**: It is the half of G2 that the other packages in this space cannot do, and the
reason the wording is fixed at publication in the first place. An answer without it is the thing
this feature exists to replace.

**Independent Test**: Publish a version, record an acceptance of it, publish a later version of the
same document, then produce the answer and confirm it carries the wording of the version actually
accepted rather than the one now in force.

**Acceptance Scenarios**:

1. **Given** an acceptance in the answer, **When** its entry is read, **Then** the wording served
   for that version is there with it.
2. **Given** an acceptance of a version that has since been superseded, **When** the answer is
   produced, **Then** it carries the superseded wording rather than what is now in force.
3. **Given** an answer produced at any later time, **When** its wording is compared with what was
   stored at publication, **Then** they are the same.
4. **Given** a person with acceptances of several versions of one document, **When** the answer is
   produced, **Then** each entry carries its own version's wording rather than one shared copy.

---

### User Story 3 - Only the people who should can produce it (Priority: P1)

Producing everything held about a person hands over personal data, so it is a privileged act rather
than something any signed-in member of staff can do. It is gated on a permission of its own, and
somebody without it cannot reach it by any route this feature adds.

**Why this priority**: A surface that assembles one person's consent history and serves it to
whoever asks is a worse problem than the one this feature solves. It ships with the permission or
it does not ship.

**Independent Test**: Attempt to produce an answer as somebody without the permission, by every
route the feature adds, and confirm each attempt is refused and reveals nothing about whether the
person has records.

**Acceptance Scenarios**:

1. **Given** a person holding the permission, **When** they produce an answer, **Then** it is
   produced.
2. **Given** somebody signed in without the permission, **When** they attempt to produce an answer,
   **Then** it is refused.
3. **Given** somebody not signed in at all, **When** they attempt to produce an answer, **Then** it
   is refused.
4. **Given** a refused attempt, **When** the refusal is read, **Then** it does not reveal whether
   the named person has any records.
5. **Given** the permission held by nobody, **When** the package is installed, **Then** no answer
   can be produced, because the permission is granted deliberately rather than by default.

---

### User Story 4 - An answer for a person whose account is gone (Priority: P2)

A request about somebody who closed their account is the ordinary case rather than the exotic one,
and it is often exactly the person who makes a request. Where records survived the removal of an
account, the answer finds them and produces them like any other.

**Why this priority**: The records exist for this. P2 rather than P1 because it depends on what
FS-003 leaves behind and the three stories above are what make an answer exist at all.

**Independent Test**: Record acceptances for a person, remove their account under the setting that
keeps records, then produce the answer for that person and confirm their acceptances and wording
come back complete.

**Acceptance Scenarios**:

1. **Given** a person whose account has been removed and whose records survived, **When** the
   answer is produced for them, **Then** their acceptances are in it.
2. **Given** such an answer, **When** it is read, **Then** each entry still names the person, the
   version and the time, and carries the wording served.
3. **Given** a person whose account has been removed under the setting that removes records,
   **When** the answer is produced for them, **Then** it states that nothing is held.
4. **Given** a mix of people with and without accounts, **When** an answer is produced for one of
   them, **Then** it contains nothing belonging to anybody else.

---

### User Story 5 - The answer says what it covers, and what it does not (Priority: P1)

A person asking what a site holds about them is rarely asking only about consent, and an answer
that looks complete but covers one application is worse than no answer. So the answer states in
plain language what it covers: what this package holds, and nothing the project holds elsewhere.

**Why this priority**: It is the constitution's rule about what the package may imply, applied at
the one point where the package's output is handed to a member of the public. An answer that
implies completeness it does not have is the failure mode, and it costs nothing to prevent.

**Independent Test**: Produce an answer and confirm it carries a plain statement of what it covers,
and that neither it nor anything around it claims to answer a request in full or to satisfy any
regulation.

**Acceptance Scenarios**:

1. **Given** any produced answer, **When** it is read, **Then** it states plainly that it covers
   what this package holds and not data held elsewhere in the project.
2. **Given** an answer stating nothing is held, **When** it is read, **Then** it carries the same
   statement, because "nothing here" is not "nothing anywhere".
3. **Given** the answer and the documentation around it, **When** either is read, **Then** neither
   claims the answer satisfies a request in full or names any regulation.

---

### Edge Cases

- A person has acceptances of a document that has since had ten more versions published. Every
  acceptance they hold appears, each carrying the wording of the version they actually accepted.
- A person's records are produced, then erased under issue #22, then produced again. The second
  answer states that nothing is held.
- Two people share a display name. The answer is produced for one identified person and carries
  nothing belonging to the other.
- A person has a single acceptance of a document whose wording is very long. The answer carries it
  in full, because an abridged answer is not evidence.
- Somebody without the permission guesses the address or the command. They are refused and learn
  nothing about whether the person exists.
- An answer is produced for somebody who has never signed in and has no account at all. Nothing is
  held, and the answer says so.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST be able to produce, for one named person, everything it holds about
  them, as a single answer rather than a set of separate lookups. *(US-1)*
- **FR-002**: The answer MUST contain every acceptance held for that person, including several
  acceptances of the same document. *(US-1)*
- **FR-003**: Each entry MUST name the document, the version accepted, and the moment it happened.
  *(US-1)*
- **FR-004**: The answer MUST contain nothing belonging to any other person. *(US-1, US-4)*
- **FR-005**: An answer for a person the package holds nothing about MUST state that nothing is
  held, and MUST NOT be an error. *(US-1)*
- **FR-006**: Producing the same answer twice with no change to the records MUST give the same
  result. *(US-1)*
- **FR-007**: Each entry MUST carry the wording served for the version it names, taken from what
  was stored at publication. *(US-2)*
- **FR-008**: An entry for a superseded version MUST carry that version's wording rather than the
  wording now in force. *(US-2)*
- **FR-009**: Each entry MUST carry its own version's wording, with no entry borrowing another's.
  *(US-2)*
- **FR-010**: The package MUST NOT produce the wording by rendering the source again at the time
  the answer is produced. *(US-2)*
- **FR-011**: Producing an answer MUST require a permission of its own, held by nobody by default.
  *(US-3)*
- **FR-012**: Every route this feature adds MUST refuse a request from somebody without that
  permission, including somebody not signed in. *(US-3)*
- **FR-013**: A refusal MUST NOT reveal whether the named person has any records. *(US-3)*
- **FR-014**: The answer MUST include acceptances that survived the removal of the account they
  name. *(US-4)*
- **FR-015**: The answer MUST carry a plain statement that it covers what this package holds and
  not data held elsewhere in the project, including when nothing is held. *(US-5)*
- **FR-016**: The answer and its documentation MUST NOT claim that it satisfies a request in full,
  and MUST NOT name any regulation. *(US-5)*
- **FR-017**: The answer MUST be able to carry a further kind of record without its shape changing,
  so that the cookie choices in R8 join it rather than arriving as a second answer. *(US-1)*
- **FR-018**: This feature MUST offer no way for a host project to attach data from its own models
  to the answer. *(US-5)*

### Key Entities

*Document*, *Version* and *Acceptance* are defined by FS-001 and FS-003 and are unchanged here.
This feature adds no stored data. It reads what those features hold and assembles it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a person with acceptances across four documents, including three versions of one
  of them, the answer contains all of them and nothing belonging to anybody else.
- **SC-002**: Every entry's wording is identical to what was stored for that version at
  publication, including for versions long superseded.
- **SC-003**: Every route the feature adds refuses somebody without the permission, with one test
  per route and no route left untested.
- **SC-004**: A refusal for a person with records and a refusal for a person without them are
  indistinguishable.
- **SC-005**: An answer for a person with no records states that nothing is held and carries the
  same statement of coverage as a full one.
- **SC-006**: Acceptances that outlived their account appear in the answer, complete with wording.
- **SC-007**: The answer and its documentation contain no claim of completeness beyond this package
  and no mention of any regulation.
- **SC-008**: Producing an answer costs a number of lookups that does not grow with the number of
  documents a site runs.

## Clarifications

### Session 2026-09-21

- **Q**: Is this the package's single answer about a person, or a report about acceptances that
  R8 and R9 will each duplicate for their own records? → **A**: The single answer (FR-017). Built
  now over acceptances because that is all the package holds, and shaped so cookie choices join it
  when R8 arrives. Sam's ruling. The alternative leaves a site with two or three places to look for
  what one person consented to, which is the problem this feature exists to remove.
- **Q**: Who is the audience, and does the person themselves use this? → **A**: Whoever is fielding
  the request, gated on a permission of its own (FR-011). The person's own view of what they agreed
  to is R9, which reads the same facts for a different audience and cannot share this permission.
- **Q**: Is producing an answer itself recorded, the way erasure is? → **A**: No. Reading is not
  changing, and a log of who looked at whose data is more personal data about people who did not ask
  for it. A site needing to evidence that it responded to a request has a process question rather
  than a gap in this package. Raised separately at the spec gate rather than folded in.
- **Q**: Does the answer carry the wording in full, or a reference to it? → **A**: In full
  (FR-007). The wording is the evidence, a reference can resolve to something else later, and an
  abridged answer is not an answer. The cost is that an answer can be large, which is accepted.
- **Q**: Can a host project attach its own data to the answer? → **A**: Not here (FR-018). That is
  R11, aspirational, and the constitution is explicit that a partial answer presented as a complete
  one is worse than no answer. This feature answers for what the package holds and says so.

## Assumptions

- The answer is produced by somebody who already works in the site's staff surfaces, rather than at
  a new place of its own. Which surface belongs to planning rather than here.
- One person at a time. Producing answers in bulk is not this feature, and the site-wide picture is
  R10.
- The wording served is what FS-001 stores at publication. This feature holds no copy of its own
  and stores nothing.
- A person can be reduced to the identifier their records carry before this page is asked. While
  the account exists, a username or an email address does that. Once it is gone, only the host
  project knows which identifier belonged to whom, and keeping that map is the project's
  responsibility rather than this package's.
- Cookie choices are absent because nothing records them yet. R8 brings them, and FR-017 is what
  stops that being a second answer.
- The answer's form is not fixed here. What matters is that it can be handed to somebody, carries
  the wording in full, and is the same twice.
- FS-001 and FS-003 are both specified and not yet delivered. This spec is written against their
  specifications.
