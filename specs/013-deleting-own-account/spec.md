# Feature Specification: A person deletes their account and their data

**Feature Branch**: `013-deleting-own-account`

**Created**: 2026-10-23

**Status**: Draft

**Serves**: G9 · **Roadmap**: R11 · **Issue**: #48

**Input**: A signed-in person should be able to ask for their account and their data to be deleted,
from the same account area where they manage everything else. Deletion here means the account is
really gone, not deactivated or hidden. The package provides the page, its place in the account
area, and the confirmation a person goes through before anything happens, so a project does not
build or style any of it. It does not reach into the project's data itself. The project decides
what deleting a person means for its own data and does it in its own code, connected through a
hook. The person's acceptances are not part of what gets deleted. They are the evidence of what
that person agreed to, and they stay, as the package already does when an account is removed.

## Scope

The package adds one page to the account area. It tells the signed-in person what deleting their
account will remove and that it cannot be undone, asks them to confirm it is them, and asks them to
confirm they mean it. Then the host project's own code deletes what the project holds about them,
the package removes the account, the person is signed out, and they are told it is done.

What deleting a person means for the project's data is the project's to say. The kinds of record a
project already declares for a person's copy of their data (FS-012) are the same kinds it says how
to delete, one kind at a time. The page lists those kinds, so what a person is told will be deleted
and what the project actually deletes come from one place.

The page exists only on a site that has said how every kind it declares is deleted. A site that has
said nothing about deletion gets no page and no menu entry, and a site that declared its kinds for
the copy alone keeps working exactly as before.

Some things stay out of this feature:

- Downloading a copy of one's data is FS-012. This page points to it, and changes nothing about it.
- Preparing a copy in the background is #116.
- A waiting period before the deletion takes effect, a way to undo it, or a member of staff
  approving it. The deletion happens when the person confirms.
- Deleting another person's account. Every route the feature adds acts on the signed-in person
  only.
- What a person has agreed to. Their acceptances follow the project's existing setting for when an
  account is removed (ADR 0008), and nothing here offers another way to remove them (ADR 0015).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deleting my account (Priority: P1)

A person has decided to stop using a site. They open the account area and find an entry for
deleting their account beside the ones for their profile, their data and what they have agreed to.
The page lists, one line for each kind of record, what the site will delete about them, and says
plainly that the account and those records will be gone for good. Where the site offers a copy of
their data, the page points them to it first. They confirm it is them, then confirm they want the
account deleted. The site deletes it, signs them out, and shows them a page saying their account
has been deleted. Signing in with their old details no longer works.

A deletion is complete or it does not happen: if part of the site's data cannot be deleted, the
person is told it could not be done and their account is still there, rather than left with an
account that is half gone. And it is always the person's own act, so somebody who has found a
signed-in browser cannot delete the account with it.

**Why this priority**: It is the feature.

**Independent Test**: In a project that declares two kinds of record and says how each is
deleted, give a person records of both kinds and some acceptances. Ask to delete the account as
that person and confirm they must confirm their identity and then confirm the deletion. Confirm
afterwards that the account is gone, the project's deletion ran for both kinds, the person is
signed out and shown the page saying it is done, their acceptances are still recorded, and another
person's records are untouched. Make one kind fail and confirm the account and every record are
still there.

**Acceptance Scenarios**:

1. **Given** a site that says how every declared kind is deleted, and a signed-in person, **When**
   they open the account area, **Then** its menu has an entry for deleting their account, and
   following it opens the page.
2. **Given** the page, **When** the person opens it, **Then** it names every declared kind the
   deletion will remove, in the order the project declared them, states that the deletion cannot
   be undone, and opening it has deleted nothing. Neither the page nor anything after it claims the
   deletion removes everything the site holds or names any regulation.
3. **Given** a site that also offers a person a copy of their data, **When** the page is shown,
   **Then** it links to that page before the person is asked to confirm anything.
4. **Given** somebody not signed in, **When** they open the page or ask for a deletion, **Then**
   they are sent to sign in and nothing is deleted.
5. **Given** a signed-in person who has not confirmed their identity recently, **When** they ask
   for the deletion, **Then** they are asked to confirm it is them, and nothing is deleted until
   they have. One who confirmed a moment ago is not asked again. An account with nothing to confirm
   with, no password and no second factor, is treated as having confirmed, as for a copy of their
   data.
6. **Given** a person who has confirmed it is them, **When** they ask for the deletion without
   confirming that they want the account deleted, **Then** nothing is deleted and they are asked
   to confirm it.
7. **Given** a person who has confirmed both, **When** the deletion runs, **Then** the project's
   deletion runs once for each declared kind, for that person, in the declared order, and then the
   account itself is removed.
8. **Given** a deletion that has completed, **When** the person's browser makes its next request,
   **Then** they are no longer signed in, in that browser or in any other where the account was
   signed in, and they see a page saying the account has been deleted.
9. **Given** an account that has been deleted, **When** anyone tries to sign in with its details,
   **Then** the sign-in fails as it would for an account that never existed.
10. **Given** a person who has accepted documents, **When** their account is deleted on a site
    using the package's default setting, **Then** every one of their acceptances is still recorded,
    still naming the version accepted and when, and no longer linked to an account. On a site that
    has set acceptances to go with a removed account, they go with it, as for any account removal.
11. **Given** two people with records of the same kinds, **When** one of them deletes their
    account, **Then** nothing belonging to the other is changed, and no route the feature adds
    accepts a person, an account or an identifier.
12. **Given** a declared kind whose deletion fails, **When** the person confirms the deletion,
    **Then** the account is still there, nothing held in the database about them has changed, they
    are still signed in, and they are told the deletion could not be done in words that reveal
    nothing about the project's internals. The failure is reported to the project, naming the kind
    that caused it.

---

### User Story 2 - A developer says how the project deletes what it holds about a person (Priority: P1)

A developer's project already declares, for the copy of a person's data, a profile and the datasets
a person uploaded. They want people to be able to delete their accounts. For each kind they already
declared, they say what deleting a person does to it: the datasets are deleted, and the profile is
deleted with the account by the project's own models, so there is nothing more to do for it. Once
every kind says so, the deletion page appears in the account area, listing both kinds, with no
template, view or styling from the project.

Some of what the project holds is not removed by deleting rows: a file in storage, a subscription
held by another service, a record that must be kept and stripped of the person's details instead.
For those the developer writes the kind's deletion in their own code, and it runs at the same point
as every other kind.

**Why this priority**: Without it there is nothing to delete but the account, and only the project
knows what else a person has left behind. This is what makes the page honest.

**Independent Test**: Declare one kind whose records are deleted with the person, one whose records
go with the account by themselves, and one whose deletion is the project's own code. Delete a
person's account and confirm each kind's deletion ran as declared. Then declare a kind that says
nothing about deletion beside ones that do, and confirm the project reports it at start-up.

**Acceptance Scenarios**:

1. **Given** a project whose declared kinds each say how a person's records of that kind are
   deleted, **When** it runs, **Then** the deletion page and its menu entry exist.
2. **Given** a declared kind that says its records are deleted with the person, **When** a
   person's account is deleted, **Then** that person's records of that kind are gone and nobody
   else's are.
3. **Given** a declared kind that says its records go with the account and need nothing more,
   **When** a person's account is deleted, **Then** the package does nothing for that kind before
   removing the account.
4. **Given** a declared kind whose deletion is the project's own code, **When** a person's account
   is deleted, **Then** that code runs once, for that person, before the account is removed.
5. **Given** a project whose declared kinds say nothing about deletion, or that declares no kinds
   at all, **When** it runs, **Then** there is no deletion page and no menu entry, nothing fails,
   and the copy of a person's data works as before.
6. **Given** a project where some declared kinds say how they are deleted and others do not,
   **When** the project starts, **Then** each kind that says nothing is reported as an error at
   start-up rather than on the first request.

---

### User Story 3 - A project hears about every account deleted (Priority: P3)

A site may need to note that an account was deleted at its owner's request, cancel something held
elsewhere, or send the person a last email. The package keeps no record of a deletion, but it tells
the project each time one has completed, and the project decides what to do.

**Why this priority**: The package stores nothing about a deletion, by design. Projects that need a
trace or a follow-up need a way to make one, and this is the smallest.

**Independent Test**: Connect the project's own code to the notice, delete an account, and confirm
the code is told once, after the account is gone, naming the account that was removed and the kinds
deleted. Make a deletion that fails and confirm the code is not told.

**Acceptance Scenarios**:

1. **Given** project code listening for the notice, **When** a person's account is deleted,
   **Then** it is told once, after the deletion has completed, with the removed account's identity
   and the kinds deleted.
2. **Given** a deletion that could not be done, **When** the attempt ends, **Then** the notice is
   not sent.
3. **Given** project code listening for the notice that fails, **When** a person's account is
   deleted, **Then** the account stays deleted and the person is still told it is done.

---

### Edge Cases

- A person asks for the deletion twice, in two tabs. The first deletes the account. The second
  finds nobody signed in and sends them to sign in, and nothing else happens.
- A person's session ends between confirming their identity and confirming the deletion. They are
  sent to sign in and nothing is deleted.
- A person holds no records of a declared kind. The kind is still listed on the page, and its
  deletion runs and finds nothing to delete.
- The person is the site's only superuser. The package treats the account like any other. A
  project that must keep one makes its own code for a kind refuse, and the deletion does not
  happen.
- A person reads the site in German. The page, its confirmations and the page saying the account
  has been deleted are in German where translations exist.
- The person published a version of a document. The version still names its publisher as
  "Account removed", as it already does for any removed account.
- The site's account area is not mounted. There is no page and nothing fails.
- A file the project's code deletes from storage cannot be restored if a later kind fails. The
  project's own code chooses the order its kinds are declared in, and a kind whose deletion cannot
  be undone is best declared last.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST add a page to the account area from which a signed-in person deletes
  their own account, with an entry in the account area's menu. *(US-1)*
- **FR-002**: The page MUST list every declared kind the deletion will remove, in the declared
  order, and MUST state that the deletion cannot be undone. *(US-1, US-2)*
- **FR-003**: Opening the page MUST delete nothing. A deletion MUST happen only by an action the
  person takes that cannot be triggered by following a link. *(US-1)*
- **FR-004**: Where the site offers a person a copy of their data, the page MUST link to it before
  the person is asked to confirm anything. *(US-1)*
- **FR-005**: Somebody not signed in MUST be sent to sign in, and MUST NOT be able to delete
  anything. *(US-1)*
- **FR-006**: A deletion MUST NOT run until the person has confirmed their identity, unless they
  did so recently, or their account has nothing to confirm with and the site's sign-in treats it
  as confirmed. *(US-1)*
- **FR-007**: A deletion MUST NOT run until the person has also confirmed, as a separate act, that
  they want the account deleted. *(US-1)*
- **FR-008**: No route the feature adds MAY accept a person, account or identifier. A deletion MUST
  always be of the signed-in person's own account, and the package MUST ask each declared kind to
  delete that person's records only. *(US-1)*
- **FR-009**: A deletion MUST run each declared kind's deletion once, in the declared order, and
  then remove the account. *(US-1, US-2)*
- **FR-010**: After a deletion, the person MUST be signed out wherever the account was signed in,
  and MUST be shown a page saying the account has been deleted. *(US-1)*
- **FR-011**: If any declared kind's deletion fails, the account MUST NOT be removed, nothing held
  in the database about the person MAY have changed, the person MUST remain signed in, and they
  MUST be told the deletion could not be done in words that reveal nothing about the project's
  internals. *(US-1)*
- **FR-012**: Such a failure MUST be reported through the project's error reporting, naming the
  kind that failed and carrying the original error. *(US-1)*
- **FR-013**: The person's acceptances MUST be kept or removed with the account exactly as the
  existing account-removal setting says, and the feature MUST offer no other way to remove them.
  *(US-1)*
- **FR-014**: A developer MUST be able to say, for each kind declared in the project's settings,
  how a person's records of that kind are deleted. *(US-2)*
- **FR-015**: A declared kind MUST be able to say its records are deleted with the person, with no
  code beyond the declaration it already has. *(US-2)*
- **FR-016**: A declared kind MUST be able to say its records go with the account and need nothing
  more. *(US-2)*
- **FR-017**: A declared kind MUST be able to have its deletion done by the project's own code.
  *(US-2)*
- **FR-018**: The deletion page and its menu entry MUST exist only when every declared kind says
  how it is deleted. With no kind saying so, there MUST be no page and nothing MAY fail. *(US-2)*
- **FR-019**: Declared kinds of which some say how they are deleted and some do not MUST be
  reported as an error when the project starts. *(US-2)*
- **FR-020**: Neither the page, anything shown after it, nor the documentation MAY claim the
  deletion removes everything the site holds, or name any regulation. *(US-1)*
- **FR-021**: The package MUST tell the project, once, each time a deletion completes, with the
  removed account's identity and the kinds deleted, and MUST NOT tell it when a deletion could not
  be done. *(US-3)*
- **FR-022**: A failure in project code told about a deletion MUST NOT undo the deletion or stop
  the person being told it is done. *(US-3)*
- **FR-023**: The package MUST keep no record of a deletion. *(US-3)*
- **FR-024**: Every word the page, its confirmations and the page after it show a person MUST be
  translatable. *(US-1)*

### Key Entities

- **Account deletion**: a signed-in person removing their own account, after the project's code
  has deleted each kind of record the project declares about them. Not stored anywhere. It leaves
  the person's acceptances as the project's account-removal setting says.
- **Declared kind**: unchanged from FS-012, and now also saying how a person's records of that kind
  are deleted.

*Document*, *Version* and *Acceptance* are unchanged. This feature adds no stored data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer whose kinds are already declared for the copy makes the deletion page
  appear by adding, to each kind, a line or two saying how it is deleted, with no template, style or
  view of their own.
- **SC-002**: For a person with records in three declared kinds and acceptances of two documents,
  deleting the account removes the account and every record of every kind, keeps every
  acceptance under the default setting, and changes nothing belonging to anybody else.
- **SC-003**: Every route the feature adds that acts on an account refuses somebody not signed in,
  with one test per route.
- **SC-004**: No deletion runs for a person with a password or a second factor who has not
  confirmed their identity recently, nor for anyone who has not confirmed the deletion itself.
- **SC-005**: When any declared kind's deletion fails, the account and every database record about
  the person remain, in every case tested.
- **SC-006**: After a deletion, no session for the account remains and its details cannot be used
  to sign in.
- **SC-007**: The page, everything shown after it and the documentation contain no claim that the
  deletion removes everything the site holds, and no mention of any regulation.

## Clarifications

### Session 2026-10-23

- **Q**: Who removes the account itself, the package or the project's code? → **A**: The package,
  after every declared kind's deletion has run (FR-009). Leaving it to each project's code would
  let a page that says the account is deleted sit on a site where it is not. Agreed with Sam before
  the spec. Article XIII says the package never deletes data held in another application's models,
  and the account belongs to the project's user model, so the build amends that article to name
  this one removal, and a new ADR records it.
- **Q**: How does a project say what deleting a person means for its data? → **A**: Through the
  kinds it already declares for the copy (FS-012), each saying how its records are deleted
  (FR-014 to FR-017). One declaration then covers what a person can see about themselves and what
  they can delete, and the page's list of what will be deleted is the same list the deletion
  runs. A separate hook would let the two drift apart.
- **Q**: Does adding deletion break a project that declared its kinds for the copy alone? →
  **A**: No (FR-018). A project whose kinds say nothing about deletion gets no page and no error.
  Saying how one kind is deleted is the project starting to offer deletion, so from then on a kind
  that says nothing is an error at start-up (FR-019): a deletion that skipped a kind would tell the
  person something untrue.
- **Q**: Is the deletion immediate? → **A**: Yes. No waiting period, no undo, no staff approval.
  Agreed with Sam before the spec. A site that wants a period of grace builds it on the notice
  (US-3).
- **Q**: What happens to the person's acceptances? → **A**: Whatever the existing account-removal
  setting says (FR-013, ADR 0008), kept by default. This feature adds no route that removes one
  (ADR 0015).

## Assumptions

- The account area is django-mvp's, as for the copy of a person's data (FS-012). Its menu entry
  follows ADR 0020. The issue that asked for this feature names django-accounts-center, which is no
  longer maintained.
- How a person confirms it is them is the site's sign-in's own confirmation, django-allauth's,
  exactly as for a copy of their data (ADR 0028).
- Removing the account is Django's own deletion of the user, so whatever the project's models
  remove or keep when a user is deleted happens as it does for any account removal.
- "Nothing held in the database has changed" after a failure holds for records in the database.
  Files or services outside it that a kind's own code has already changed are that code's
  responsibility, and the documentation says so.
- The person is signed out by the account ceasing to exist. The page they see afterwards needs
  nobody signed in.
