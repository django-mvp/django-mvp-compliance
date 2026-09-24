# Feature Specification: Announcing that a version was published

**Feature Branch**: `005-announcing-a-version-published`

**Created**: 2026-09-24

**Status**: Draft

**Serves**: G1 · **Roadmap**: — · **Issue**: #12

**Input**: When a version of a legal document goes live, more than one person usually wants to know.
The people who own the wording are often not the people who run the site, and a policy taking
effect is the kind of event a second pair of eyes is expected to have seen. Right now the only way
to find out is to go and look. Whoever is responsible for a site should learn that a document was
published without watching for it: who published it, which document, and when.

## Scope

When a version is published, the package announces it with a `version_published` signal. The host
project listens for it and runs its own code: an email, a message in a chat channel, an entry in
an audit log, or nothing. The package decides nothing about who is told, how, or when, and it never
sends anything itself.

The signal names the person who published the version, and the package does not record that today.
So this feature also has each version keep a permanent record of who published it, frozen with the
rest of what was published.

Alongside the signal, the package ships a ready-made plain-text email for the people who run the
site. It is translatable, rendered by Django's template system, and replaced by putting a template
of the same name in the project. The package renders it and hands back the subject and body. The
project chooses who receives it and sends it.

An email to the site's users about a new version is issue #42. It needs a public page for the
document to link to and a summary of what changed, and neither exists yet. Telling readers what
changed is R6, and the site-wide picture of where a site stands is R10. Keeping a record of who
produced a person's consent records is issue #35. How versions are numbered is issue #38, and this
feature uses whatever number a version has.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A project hears about every publication (Priority: P1)

A developer on a host project wants to act when a document's wording changes: tell the site's
owners, post to a channel, or write to the project's own audit trail. They connect one receiver to
`version_published`, and it runs every time a version goes live with everything needed to say what
happened: the version, who published it, and the version it replaced.

A publication that did not happen must never be announced. A receiver that tells people "the new
terms are in force" about a version that was refused, or rolled back, is worse than silence. And a
receiver is the project's code, so when it fails, the failure stays the project's problem. The
version is in force either way, and the person who published it should not be told otherwise.

**Why this priority**: It is the feature. Everything else here exists to make the announcement
complete or easier to use.

**Independent Test**: Connect a receiver, publish a draft, and confirm the receiver ran once with
the version, the publisher and the version it replaced. Then attempt each publication the package
refuses and confirm the receiver never ran.

**Acceptance Scenarios**:

1. **Given** a receiver connected to `version_published`, **When** a draft is published, **Then**
   the receiver runs exactly once.
2. **Given** that receiver, **When** it runs, **Then** it receives the version published, the
   person who published it, and the version it replaced.
3. **Given** a document with no version in force, **When** its first version is published, **Then**
   the receiver is told that no version was replaced.
4. **Given** a version that publishing refuses (already published, empty once rendered, or saying
   exactly what the version in force says), **When** publishing is attempted, **Then** the receiver
   does not run.
5. **Given** a publication inside a transaction that is later rolled back, **When** the transaction
   ends, **Then** the receiver has not run.
6. **Given** a publication inside a transaction that commits, **When** the receiver runs, **Then**
   the version it is handed is already in force, and any query the receiver makes sees it that way.
7. **Given** a receiver that raises an error, **When** a draft is published through the admin,
   **Then** the version is in force, the person publishing is told it was published, and the error
   is logged.
8. **Given** two receivers where the first raises an error, **When** a draft is published, **Then**
   the second still runs.

---

### User Story 2 - A version records who published it (Priority: P1)

Writing a version and publishing it need different permissions, so the person who wrote a wording
is often not the person who put it in force. Once a wording is live, "who approved this?" is the
first question anybody asks, and today nothing answers it. Each version now keeps its publisher,
set at the moment it is published and never changed afterwards, and the admin shows it wherever it
shows the moment of publication.

Not every publication has a person behind it. A data migration or a shell session can call
`publish()` directly, and that stays allowed. The version then says no publisher was recorded,
rather than inventing one.

The person who published a version may later have their account removed. The version stays, and it
still tells "published by an account since removed" apart from "no publisher recorded".

**Why this priority**: The announcement names the publisher, and it cannot name somebody the package
never recorded. It is also the part of this feature that lasts. An announcement goes out once, and
the record answers the question years later.

**Independent Test**: Publish a draft through the admin as one person and confirm the version names
them, that nothing can change it afterwards, and that the admin shows it. Publish another from code
with no person and confirm it says no publisher was recorded.

**Acceptance Scenarios**:

1. **Given** a person holding the publish permission, **When** they publish a draft through the
   admin, **Then** the version records them as its publisher.
2. **Given** a published version, **When** anything tries to change its publisher by any route that
   refuses other changes to a published version, **Then** it is refused the same way.
3. **Given** a draft, **When** it is published from code with no person given, **Then** it
   publishes, and the version records that no publisher was recorded.
4. **Given** a published version, **When** its page or its document's version list is viewed in
   the admin, **Then** the publisher is shown next to the moment of publication.
5. **Given** a version published before this feature existed, **When** it is viewed, **Then** it
   shows that no publisher was recorded and is attributed to nobody.
6. **Given** a version whose publisher's account is removed, **When** the removal runs, **Then** it
   succeeds, the version is otherwise unchanged, and the version shows its publisher's account as
   removed.
7. **Given** a draft, **When** it is viewed, **Then** it has no publisher.

---

### User Story 3 - A ready-made email for the people running the site (Priority: P2)

Most projects that listen for the signal will send the same email: a document was published, which
one, by whom, and when. A developer should be able to send that from their receiver in a few lines,
without first writing, wording and translating it. The package ships a subject template and a body
template, and one call renders both from the values the signal carries. The project decides who
gets it and whether it is sent at all.

A project that wants different wording puts a template of the same name in its own templates and
changes nothing else. A site working in another language gets the email in whichever language is
active when it is rendered.

**Why this priority**: The signal alone meets the need. The email saves every project writing the
same one. Worth having, but the feature stands without it.

**Independent Test**: From a receiver, render the email for a publication and confirm the subject
is one line and the body names the document, the version, the publisher, the moment and the version
replaced, and links to the version in the admin. Override the body template in a test project and
confirm the override is used.

**Acceptance Scenarios**:

1. **Given** a publication, **When** the email is rendered from the values the signal carries,
   **Then** a subject and a plain-text body are returned and nothing is sent.
2. **Given** that email, **When** it is read, **Then** it names the document, the version's number,
   who published it, when, and which version it replaced.
3. **Given** a document's first publication, **When** the email is rendered, **Then** it says this
   is the document's first version in force instead of naming a replaced one.
4. **Given** a version with no publisher recorded, **When** the email is rendered, **Then** it says
   so rather than leaving a blank.
5. **Given** the site's address supplied by the project, **When** the email is rendered, **Then** it
   carries a full link to the version's page in the admin.
6. **Given** a project template at the same path as the package's, **When** the email is rendered,
   **Then** the project's template is used.
7. **Given** a language other than English active when it is rendered, and a catalog for that
   language, **When** the email is rendered, **Then** it is in that language.
8. **Given** any rendering, **When** the subject is read, **Then** it is a single line, whatever the
   document is called.

---

### Edge Cases

- Two drafts of one document are published at nearly the same moment. Each publication that
  succeeds is announced once, and the second names the first as the version it replaced. One
  refused because the other got there first is not announced.
- Two documents are published in one transaction. Each is announced once, after it commits.
- A receiver publishes another version itself. That publication is announced in the usual way, and
  the first announcement is unaffected.
- A document's name contains a line break or characters that look like markup. The subject stays
  one line, and the plain-text body carries the name as written, with nothing escaped for HTML.
- A publisher's account is removed and the version's page is opened afterwards. It says the account
  was removed and names nobody.
- A version is published by an account with no name or email address. The publisher is still
  recorded, and the email identifies them the way the admin does.
- No receiver is connected. Publishing behaves exactly as it does today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST provide a `version_published` signal, sent each time a version is
  published. *(US-1)*
- **FR-002**: The signal MUST carry the version published, the person who published it or none, and
  the version it replaced or none. Its sender MUST be the version model. *(US-1)*
- **FR-003**: The signal MUST be sent exactly once per successful publication, and never for a
  publication that is refused. *(US-1)*
- **FR-004**: The signal MUST be sent only after the publication is committed, and never for one
  that is rolled back. *(US-1)*
- **FR-005**: An error raised by a receiver MUST NOT undo, block or hide a publication. It MUST be
  logged, and the remaining receivers MUST still run. *(US-1)*
- **FR-006**: Publishing through the admin MUST report success when the publication succeeded,
  whatever any receiver did. *(US-1)*
- **FR-007**: The package MUST NOT send email, make a network request, or otherwise act on a
  publication itself. Acting on the signal is left entirely to the host project. *(US-1, US-3)*
- **FR-008**: Each version MUST record who published it, set at the moment of publication and
  empty for a draft. *(US-2)*
- **FR-009**: The publisher MUST be frozen with the rest of a published version, and refused by
  every route that refuses other changes to one. *(US-2)*
- **FR-010**: Publishing through the admin MUST record the person who published. *(US-2)*
- **FR-011**: Publishing from code MUST stay possible without naming a person, and the version MUST
  then record that no publisher was recorded. *(US-2)*
- **FR-012**: The admin MUST show a published version's publisher wherever it shows the moment of
  publication. *(US-2)*
- **FR-013**: Removing a publisher's account MUST NOT be blocked by the version and MUST NOT remove
  it. Afterwards the version MUST show it was published by an account since removed, distinct from
  having no publisher recorded. *(US-2)*
- **FR-014**: The version MUST NOT hold the publisher's name, email address or any identifying
  detail beyond what identifies the account. *(US-2)*
- **FR-015**: The package MUST ship a subject template and a plain-text body template for an email
  announcing a publication, rendered by Django's template system. *(US-3)*
- **FR-016**: The package MUST offer one call that renders the subject and body from the values the
  signal carries and returns them without sending anything. *(US-3)*
- **FR-017**: The email MUST name the document, the version's number, the publisher or that none
  was recorded, the moment of publication, and the version replaced or that it is the first.
  *(US-3)*
- **FR-018**: The email MUST link to the version's page in the admin, using a site address the host
  project supplies when rendering. *(US-3)*
- **FR-019**: The rendered subject MUST be a single line. *(US-3)*
- **FR-020**: Every string in both templates MUST be translatable, and the email MUST render in the
  language active when it is rendered. *(US-3)*
- **FR-021**: A project template at the same path MUST replace the package's, with no setting
  required. *(US-3)*
- **FR-022**: Nothing this feature adds MAY claim that announcing a publication makes a site
  compliant, or name a regulation. *(US-3)*
- **FR-023**: The documentation MUST list every value the signal carries and show a receiver that
  sends the ready-made email. *(US-1, US-3)*
- **FR-024**: The glossary MUST define *Publisher* as the person who put a version in force.
  *(US-2)*

### Key Entities

- **Version** (FS-001): gains its publisher. Recorded at publication, frozen from then on, and
  shown as "no publisher recorded" or "account since removed" when there is no account to name.
- **Publisher**: the person who put a version in force. Not necessarily the person who wrote it,
  because writing and publishing need different permissions.
- **Publication announcement**: the `version_published` signal and the values it carries. Nothing
  about it is stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every successful publication a connected receiver runs exactly once, and for each
  of the three refusals in `publish()` it runs zero times.
- **SC-002**: A publication inside a rolled-back transaction produces zero announcements.
- **SC-003**: With a receiver that raises an error, publishing through the admin leaves the version
  in force, shows a success message and logs the error.
- **SC-004**: Every version published through the admin names its publisher, and no route that
  refuses other changes to a published version accepts a change to it.
- **SC-005**: Removing a publisher's account succeeds and leaves every version they published in
  place.
- **SC-006**: A developer can send the ready-made email from a receiver in five lines of their own
  code or fewer, not counting choosing the recipients.
- **SC-007**: The rendered subject contains no line break for any document name, including one that
  contains one.
- **SC-008**: `makemessages` over the package picks up every string in both email templates.

## Clarifications

### Session 2026-09-24

- **Q**: Is the signal about a document or a version? → **A**: A version, named `version_published`.
  The glossary says publishing happens to a version, and a document is published many times over
  its life. Sam's ruling at intake.
- **Q**: Should the package send the email itself, to recipients named in a setting? → **A**: No
  (FR-007). Who is told, how and when is the host project's decision, and a project usually has its
  own way of doing this already. The package provides the announcement and a ready-made email to
  send from it. Sam's ruling at intake.
- **Q**: Does the ready-made email include one for the site's users? → **A**: No. That email needs
  a public page for the document and a summary of what changed, and neither exists yet. It is split
  out as issue #42. This feature ships the email for the people running the site.
- **Q**: When a receiver fails, does the publication fail with it? → **A**: No (FR-005, FR-006).
  The version is already in force when the signal is sent. Failing the request would tell the
  publisher something went wrong with a publication that succeeded, and they might try again. The
  failure is logged for the project to deal with.
- **Q**: What does a version say about its publisher once their account is removed? → **A**: That it
  was published by an account since removed, which differs from having no publisher recorded
  (FR-013). It holds nothing that names the person (FR-014), for the reason in ADR 0014: what is
  kept about a removed account is the host project's decision.

## Assumptions

- Publishing already happens in exactly one place, `Version.publish()`. This feature adds to that
  step and changes none of its refusals.
- Nothing has been released, so no published version in the wild lacks a publisher. Any in a
  development database show that no publisher was recorded.
- A signal carries no request, so the site's address for the admin link comes from the host project.
  How it supplies it is a planning question.
- The package ships an English catalog only, as for every other string.
- The publisher is new personal data about a member of staff. Under Article XV it ships with a
  CHANGELOG entry naming it in plain language.
- FS-001 and FS-002 are delivered, and this spec is written against them as they stand on main.
