# Feature Specification: A person downloads a copy of their data

**Feature Branch**: `012-copy-of-own-data`

**Created**: 2026-10-21

**Status**: Draft

**Serves**: G9 · **Roadmap**: R11 · **Issue**: #47

**Input**: A signed-in person should be able to ask the site for a copy of what it holds about them,
from the same account area where they manage everything else. Today there is nowhere to ask, so
every project builds its own page, styles it to match, and wires it into its account menu. The
package provides the page and its place in the account area, so the request looks and behaves like
the rest of the site with no template work from the project. It does not reach into the project's
data itself. Only the project knows where its data lives, so the project says what it holds about a
person, and the package turns that into the copy the person downloads.

## Scope

The package adds one page to the account area. It tells the signed-in person what a copy of their
data will contain, asks them to confirm it is them, and then gives them the copy as a single
download. The copy has a part a person can open and read with no special software, a part a program
can read, and the files they uploaded.

What goes into the copy is the host project's to say. A developer declares, in the project's
settings, each kind of thing the project holds about a person, and how to find it for one person.
The package presents every declared kind the same way, in the page and in the copy, so a site's
copy looks like the site and reads the same from one kind of record to the next. The package's own
section, what the person has agreed to and the wording they were shown, is always part of the copy.

The page exists only on a site that has declared what it holds. A project that has said nothing
gets no page and no menu entry. Without a declaration, a copy holding only the package's own
records would look like everything the site holds, and it would not be.

Some things stay out of this feature:

- Preparing the copy in the background, and telling the person when it is ready, is #116. Here
  the copy is built while the person waits.
- Asking for an account and its data to be deleted is #48.
- The admin page staff use to produce what the package holds about one person (FS-004) is
  unchanged. It still covers consent only and still offers nothing a project can add to.
- Choosing a period or a format. A copy is everything the project declares, in every form the
  copy comes in. There is nothing for the person to choose.
- Limiting how often a person can ask. Each request builds a copy afresh. A site that needs a
  limit applies its own.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Downloading a copy of my data (Priority: P1)

A person has used a site for two years. They open the account area and find an entry for their
data beside the ones for their profile and what they have agreed to. The page lists what a copy
will contain, one line for each kind of record the site holds about them. They ask for the copy,
confirm it is them, and their browser downloads one file. Inside it they find a page they can open
and read, a file a program can read, and the files they uploaded to the site.

**Why this priority**: It is the feature. Everything else here exists to make this one request
trustworthy and consistent.

**Independent Test**: In a project that declares two kinds of record, one with uploaded files, give
a person records of both kinds and some acceptances. Ask for a copy as that person and confirm the
download holds a readable part, a machine-readable part and their files, and that both parts carry
every declared kind and their acceptances.

**Acceptance Scenarios**:

1. **Given** a site that declares what it holds and a signed-in person, **When** they open the
   account area, **Then** its menu has an entry for their data, and following it opens the page.
2. **Given** the page, **When** the person reads it before asking for anything, **Then** it lists
   every kind of record the copy will contain, in the order the project declared them, and nothing
   has been gathered yet.
3. **Given** a person who has confirmed it is them, **When** they ask for the copy, **Then** they
   receive one download.
4. **Given** that download, **When** it is opened, **Then** it holds a part readable in a web
   browser with nothing installed, a part in a format a program can read, and every file the
   declared kinds name for that person.
5. **Given** the readable part and the machine-readable part, **When** they are compared, **Then**
   they carry the same records, under the same kinds, in the same order.
6. **Given** a kind of record the person has none of, **When** the copy is made, **Then** the kind
   still appears, stating that nothing of that kind is held about them.
7. **Given** a copy, **When** it is read, **Then** it says when it was made.
8. **Given** the copy has been downloaded, **When** the site's storage is examined, **Then**
   nothing of the copy has been kept.

---

### User Story 2 - Only my own data, and only once I have confirmed it is me (Priority: P1)

A copy hands over everything a site holds about a person in one file, so somebody who has merely
found a signed-in browser must not be able to take it. The person confirms it is them before a copy
is made, unless they have just done so. And the copy is always about the person asking: there is no
way to name anybody else.

**Why this priority**: A page that gives away one person's data to whoever holds their session is a
worse problem than having no page. It ships with this or not at all.

**Independent Test**: As a signed-in person who has not recently confirmed their identity, ask for a
copy and confirm the site asks them to confirm first and makes nothing until they do. Then try to
reach another person's data by every route the feature adds and confirm none exists.

**Acceptance Scenarios**:

1. **Given** somebody not signed in, **When** they open the page or ask for a copy, **Then** they
   are sent to sign in and nothing is made.
2. **Given** a signed-in person who has not confirmed their identity recently, **When** they ask for
   a copy, **Then** they are asked to confirm it is them, and no copy is made until they have.
3. **Given** a person who fails to confirm it is them, **When** the attempt ends, **Then** no copy
   is made and they can try again.
4. **Given** a person who confirmed their identity a moment ago, **When** they ask for a copy,
   **Then** they are not asked again.
5. **Given** any route the feature adds, **When** it is examined, **Then** none of them accepts a
   person, an account or an identifier: the copy is always about whoever is signed in.
6. **Given** two people with records of the same kinds, **When** one of them makes a copy, **Then**
   it holds nothing belonging to the other.
7. **Given** the page, **When** a person opens it, **Then** opening it gathers nothing: a copy is
   made only when the person asks for one, by an action that cannot be triggered by following a
   link.

---

### User Story 3 - A developer declares what the project holds about a person (Priority: P1)

A developer's project keeps a profile for each person and lets them upload datasets. They want the
copy to include both, looking like the rest of the copy, without writing a template or styling
anything. They add each one to a list in the project's settings, saying for each how to find that
person's records and which of their details to include. The page and the copy pick both up, in the
order they listed them, with each detail labelled by the name the project already gives it.

**Why this priority**: Without it the copy holds only what the package itself keeps, which is the
smallest part of what any site holds about a person. This is what makes the copy worth asking for.

**Independent Test**: Declare a kind of record by naming how to find one person's records and which
details to include. Make a copy and confirm the kind appears in both parts, its details labelled by
the names the project's models give them, with no template or style written by the project.

**Acceptance Scenarios**:

1. **Given** a project that declares a kind of record by saying how to find one person's records
   and which details to include, **When** a copy is made, **Then** that person's records of that
   kind appear in both parts of the copy, showing those details and no others.
2. **Given** a declared detail, **When** it appears in the copy, **Then** it is labelled by the
   name the project's own model already gives it, in the language the person reads the site in.
3. **Given** a declared kind that names a detail holding an uploaded file, **When** a copy is made,
   **Then** the file itself is in the download, and both parts of the copy point to it.
4. **Given** several declared kinds, **When** the page is shown and the copy is made, **Then** both
   follow the order of the declaration.
5. **Given** a project that has declared nothing, **When** it runs, **Then** there is no page and no
   menu entry for it, and nothing fails.
6. **Given** a project that declares an empty list, **When** a person opens the page, **Then** it
   is there and the copy holds only the package's own section, because the project has said that is
   everything.
7. **Given** a declaration that names something that cannot be found or used, **When** the project
   starts, **Then** it is reported as an error at start-up rather than on the first request.

---

### User Story 4 - A copy is complete, or there is no copy (Priority: P2)

Part of a project's data is unreachable when a person asks: a storage service is down, or a
declared kind has a bug. A copy missing that part would look complete and not be. So the person
gets no copy and is told it could not be made, and the developer can find out which kind failed and
why.

**Why this priority**: A partial copy presented as a whole one is the failure this package's
constitution exists to prevent. P2 because it guards US-1 rather than adding to it.

**Independent Test**: Declare a kind that fails when asked for a person's records. Ask for a copy
and confirm the person receives no download and a message saying it could not be made, and that
the failure is reported with the kind that caused it.

**Acceptance Scenarios**:

1. **Given** a declared kind that fails while the copy is being made, **When** the person asks for
   a copy, **Then** they receive no download and are told it could not be made and that they can
   try again later.
2. **Given** such a failure, **When** the project's error reporting is read, **Then** it names the
   kind that failed and carries the original error.
3. **Given** a declared file that cannot be read, **When** the copy is made, **Then** it fails as a
   whole in the same way rather than leaving the file out.
4. **Given** a failure, **When** the person sees the message, **Then** it reveals nothing about the
   project's internals.

---

### User Story 5 - The copy says what it contains, and nothing more (Priority: P2)

A person reading their copy needs to know what it covers. The page and the copy both name every
kind of record in it, and neither claims to be everything the site holds or to satisfy any law. The
person's acceptances are always among them, each with the wording they were shown.

**Why this priority**: It is the constitution's rule about what the package may imply, at the one
point where it hands a member of the public their own data.

**Independent Test**: Make a copy and confirm the page and both parts name every kind in it, that
the package's own section is present with the wording served for each version accepted, and that
nothing in the page, the copy or the documentation claims completeness or names a regulation.

**Acceptance Scenarios**:

1. **Given** any copy, **When** it is read, **Then** it names every kind of record it holds.
2. **Given** any copy, **When** it is read, **Then** it holds the person's acceptances, each naming
   the document, the version and when it was accepted, with the wording served for that version.
3. **Given** a person who has accepted nothing, **When** a copy is made, **Then** the package's own
   section is still there and states that nothing of that kind is held.
4. **Given** the page, the copy and the documentation, **When** they are read, **Then** none of
   them claims the copy is everything the site holds or that it satisfies any regulation.

---

### User Story 6 - A developer presents a kind of record their own way (Priority: P3)

Some of what a project holds about a person is not a list of records of one kind: a summary built
from several places, or a single value. Some reads badly in the standard layout. A developer can
supply that kind's records in their own way, and can give a kind its own presentation in the
readable part, while it still sits in the copy like every other kind.

**Why this priority**: The standard declaration covers most of what projects hold. This is the
escape for the rest, so the standard one never has to grow options for every case.

**Independent Test**: Declare one kind whose records are supplied by the project's own code rather
than found from one model, and another with its own presentation. Make a copy and confirm both
appear in both parts, in their declared place, under their own headings.

**Acceptance Scenarios**:

1. **Given** a declared kind whose records the project's own code supplies, **When** a copy is
   made, **Then** those records appear in both parts of the copy like any other kind.
2. **Given** a declared kind with its own presentation, **When** the readable part is opened,
   **Then** that kind is shown in its own presentation and every other kind in the standard one.
3. **Given** a kind with its own presentation, **When** the machine-readable part is read, **Then**
   it carries that kind's records in the same shape as every other kind.

---

### User Story 7 - A project hears about every copy made (Priority: P3)

A site's own process for handling requests about personal data may need to note that a person
downloaded a copy, and when. The package keeps no such record, but it tells the project each time a
copy is handed over, and the project decides what to keep.

**Why this priority**: The package stores nothing about a copy, by design. Projects that need a
trace need a way to make one, and this is the smallest.

**Independent Test**: Connect the project's own code to the notice, make a copy, and confirm the
code is told once, naming the person, after the copy is handed over. Make a copy that fails and
confirm the code is not told.

**Acceptance Scenarios**:

1. **Given** project code listening for the notice, **When** a person downloads a copy, **Then** it
   is told once, naming the person and the kinds the copy held.
2. **Given** a copy that could not be made, **When** the attempt ends, **Then** the notice is not
   sent.
3. **Given** project code listening for the notice that fails, **When** a person downloads a copy,
   **Then** the person still receives their copy.

---

### Edge Cases

- A person whose account holds hundreds of uploaded files asks for a copy. It is built while they
  wait, as large as it needs to be. Building it in the background is #116.
- A person asks for a copy twice in a row. Each is built afresh from what is held at that moment.
- A declared kind holds a detail whose value is empty for this person. The copy shows the detail
  as having no value rather than leaving it out.
- A declared detail holds a choice from a list. The copy shows the choice as a person reads it on
  the site, and the machine-readable part carries it too.
- A declared file detail is empty for one record. That record appears with no file and the copy is
  made as normal.
- Two uploaded files from different kinds share a file name. Both are in the download and neither
  overwrites the other.
- A person reads the site in German. Headings, labels and the package's own wording in the copy
  are in German where translations exist.
- A person's session ends between confirming their identity and asking for the copy. They are sent
  to sign in and nothing is made.
- The site's account area is not mounted. There is no page and nothing fails.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST add a page to the account area from which a signed-in person
  downloads a copy of their data, with an entry in the account area's menu. *(US-1)*
- **FR-002**: The page MUST list, before anything is gathered, every kind of record the copy will
  contain, in the declared order. *(US-1, US-3)*
- **FR-003**: Opening the page MUST gather nothing. A copy MUST be made only by an action the
  person takes that cannot be triggered by following a link. *(US-1, US-2)*
- **FR-004**: The copy MUST be a single download holding a part readable in a web browser with
  nothing installed, a part in a format a program can read, and every file the declared kinds name
  for that person. *(US-1, US-3)*
- **FR-005**: Both parts of the copy MUST carry the same records under the same kinds in the same
  order. *(US-1, US-6)*
- **FR-006**: A declared kind with no records for the person MUST appear in the copy, stating that
  nothing of that kind is held. *(US-1, US-5)*
- **FR-007**: The copy MUST say when it was made. *(US-1)*
- **FR-008**: The package MUST keep nothing of a copy once it has been handed over. *(US-1)*
- **FR-009**: Somebody not signed in MUST be sent to sign in and MUST receive nothing. *(US-2)*
- **FR-010**: A copy MUST NOT be made until the person has confirmed their identity, unless they
  did so recently. *(US-2)*
- **FR-011**: No route the feature adds MAY accept a person, account or identifier. A copy MUST
  always be about the signed-in person, and the package MUST ask each declared kind for that person
  only. *(US-2)*
- **FR-012**: A developer MUST be able to declare, in the project's settings, an ordered list of
  the kinds of record the project holds about a person. *(US-3)*
- **FR-013**: A declared kind MUST be expressible by saying how to find one person's records and
  which of their details to include, with no template or styling from the project. *(US-3)*
- **FR-014**: Each detail in the copy MUST be labelled by the name the project's model gives it,
  translated where a translation exists. *(US-3)*
- **FR-015**: A declared detail that holds an uploaded file MUST put the file in the download, and
  both parts of the copy MUST point to it. Files MUST NOT overwrite each other. *(US-3)*
- **FR-016**: With no declaration in the project's settings, the page and its menu entry MUST NOT
  exist. An empty declaration MUST be accepted as a declaration. *(US-3)*
- **FR-017**: A declaration naming something that cannot be found or used MUST be reported when the
  project starts. *(US-3)*
- **FR-018**: If any declared kind or any declared file fails while the copy is made, the person
  MUST receive no copy and MUST be told it could not be made, in words that reveal nothing about
  the project's internals. *(US-4)*
- **FR-019**: Such a failure MUST be reported through the project's error reporting, naming the kind
  that failed and carrying the original error. *(US-4)*
- **FR-020**: The page and both parts of the copy MUST name every kind of record the copy holds.
  *(US-5)*
- **FR-021**: The copy MUST always hold the package's own section: the person's acceptances, each
  naming the document, the version and when it was accepted, with the wording served for that
  version taken from what was stored at publication. *(US-5)*
- **FR-022**: Neither the page, the copy nor the documentation MAY claim the copy is everything the
  site holds, or name any regulation. *(US-5)*
- **FR-023**: A developer MUST be able to declare a kind whose records the project's own code
  supplies, rather than ones found from a single model. *(US-6)*
- **FR-024**: A developer MUST be able to give a declared kind its own presentation in the readable
  part without changing how it appears in the machine-readable part. *(US-6)*
- **FR-025**: The package MUST tell the project, once, each time a copy is handed over, naming the
  person and the kinds it held, and MUST NOT tell it when a copy could not be made. *(US-7)*
- **FR-026**: A failure in project code told about a copy MUST NOT stop the person receiving it.
  *(US-7)*
- **FR-027**: Every word the page and the copy show a person MUST be translatable. *(US-1, US-3)*

### Key Entities

- **Copy**: what a person downloads. Made when they ask, handed over, and never stored. Holds a
  readable part, a machine-readable part and the person's files.
- **Declared kind**: one kind of record the host project holds about a person, named in the
  project's settings, with a heading and a way to find one person's records. The package's own
  section is one too, always present and not declared.

*Document*, *Version* and *Acceptance* are unchanged. This feature adds no stored data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer adds a kind of record backed by one model to the copy with a declaration
  of a few lines and no template, style or view of their own.
- **SC-002**: For a person with records in three declared kinds, one holding uploaded files, and
  acceptances of two documents, the copy holds every record, every file and every acceptance with
  its wording, and nothing belonging to anybody else.
- **SC-003**: Every route the feature adds refuses somebody not signed in, with one test per route.
- **SC-004**: No copy is made for a person who has not confirmed their identity recently.
- **SC-005**: When any declared kind fails, no download is produced, in every case tested.
- **SC-006**: After a copy has been downloaded, nothing of it remains in the database or in the
  site's file storage.
- **SC-007**: The page, the copy and the documentation contain no claim of completeness and no
  mention of any regulation.

## Clarifications

### Session 2026-10-21

- **Q**: Does the person choose a period or a format? → **A**: No. A copy is everything the
  project declares, and it comes in both a readable and a machine-readable form, so there is
  nothing to choose. A period filter would also make every project's code filter by date, and a
  copy cut to a period looks complete when it is not. Agreed with Sam before the spec.
- **Q**: Does the page exist for a project that has declared nothing? → **A**: No (FR-016). A copy
  holding only the package's own section would look like everything the site holds. Declaring is
  the project saying what the copy covers, and an empty declaration is the project saying it holds
  nothing more. Same approach as the site-wide agreement check, which is off until a project lists
  it.
- **Q**: Does this replace the rule that nothing outside the package can add to the answer about a
  person (ADR 0012)? → **A**: For the person's own copy, yes. ADR 0012 was written for the staff
  page, which answers for consent only, and that page is unchanged. The person's copy is the place
  R11 and Article XIII expect a project's data to be reached "through a documented hook the
  project implements". FR-018 is what keeps a badly implemented hook from producing a copy that
  looks complete and is not, the risk ADR 0012 was guarding against. A new ADR records this.
- **Q**: Is a copy timestamped, given ADR 0013 says an answer carries no time of its own? → **A**:
  Yes (FR-007). ADR 0013 is about the staff answer being evidence that reads the same twice. A
  person's copy is their own file, and they need to tell two copies apart. The package's own
  section inside it still carries only the times stored on the records.
- **Q**: Is making a copy recorded? → **A**: Not by the package (FR-008, FR-025), consistent with
  FS-004: a log of reads is more personal data. The project is told and decides what to keep.
- **Q**: Built while the person waits, or in the background? → **A**: While they wait, here.
  Background preparation, and the setting that chooses between them, is #116. The way a project
  declares its kinds does not depend on a request, so switching later needs no change to a
  project's declarations.

## Assumptions

- The account area is django-mvp's, as for the list of what a person has agreed to (FS-008). Its
  menu entry follows ADR 0020.
- How a person confirms it is them follows whatever the site's sign-in already offers. A site whose
  accounts have no password still needs a way to confirm, and research settles how.
- The uploaded files a copy holds are ones the project's models point to in the site's file
  storage. Files kept anywhere else are reached through a kind the project supplies itself (US-6).
- A copy is built in one request. A copy too large for that is #116's problem to solve.
- The package's own section uses what FS-004 already assembles about a person, rather than a second
  way of reading acceptances.
