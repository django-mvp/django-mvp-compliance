# Feature Specification: What a person has agreed to, in their account area

**Feature Branch**: `008-agreed-documents-in-account-area`

**Created**: 2026-10-01

**Status**: Refined

**Refined**: 2026-10-01. After the prototype was reviewed on screen: the document page's layout
changes with this feature, and a long history is folded (FR-019).

**Serves**: G8 · **Roadmap**: R9 · **Issue**: #66

**Input**: A signed-in person should be able to see, in the account area django-mvp provides, every
document they have agreed to: which version, and when. Each entry links to that version's page, so
they can read again exactly what they accepted, and says whether a newer version is now in force
that they have not accepted yet. Today the only place a person sees that they agreed is the
document's own page, and only if they already know where to look. The list belongs to the person,
so it shows their own records and nobody else's, and it lives where they already manage their
account. Notices do not appear in it.

## Scope

The package adds one page to the account area. It lists the documents the signed-in person has
agreed to. Under each document are the versions of it they accepted, each with its version number
and the date of the acceptance, and each linking to that version's own page. Where a newer version
of a document is in force and the person has not accepted it, the document's entry says so and
links to the version in force.

The page is read-only and is always about the person reading it. It has an entry in the account
area's menu, so a person finds it without knowing its address.

Some things stay out of this feature:

- Asking a person to accept the version in force is R4. This page reports that a newer version
  exists and offers no way to accept it.
- Documents a person has never agreed to are not listed, whether or not they have a version in
  force. Telling a person what they still have to accept belongs to R4 and R5.
- What a person chose about cookies is the other half of R9 and depends on R8. Nothing about
  cookies appears on this page.
- The page staff use to produce everything held about one person (FS-004) is unchanged. This page
  shows the document, the version and the date. Anything else kept on an acceptance is shown only
  there.
- ~~The design of the document page is issue #71. This feature links to that page and changes
  nothing on it.~~ Changed in review of the prototype: the document page's layout changes with this
  feature. Its list of documents moves into a column of its own beside the document. What the page
  shows, who can read it and its addresses do not change. The rest of #71 stays open.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seeing what I agreed to, where I manage my account (Priority: P1)

A person signed up to a site a year ago and accepted its terms and its privacy policy. The privacy
policy has been reworded since and they accepted the new version too. They open the account area,
see an entry for the documents they have agreed to, and follow it. The page lists the terms with
the one version they accepted, and the privacy policy with both versions they accepted, newest
first. Each version shows its number and the date they agreed, and following one opens that exact
version, superseded or not.

**Why this priority**: It is the feature. Without it a person has no place to find what they
agreed to, and the records the package keeps are visible only to staff.

**Independent Test**: Record acceptances of several versions of several documents for one user,
and of others for a second user. Signed in as the first, open the page from the account area's
menu and check it lists exactly the first user's documents and versions, each linking to the right
version's page.

**Acceptance Scenarios**:

1. **Given** a signed-in user who accepted one version of one document, **When** they open the
   page, **Then** it lists that document with that version's number and the date of the acceptance.
2. **Given** a user who accepted three versions of the same document, **When** they open the page,
   **Then** the document appears once with all three versions under it, the most recently
   published first.
3. **Given** a listed version that is current, **When** the user follows it, **Then** they reach
   the document's page showing that version.
4. **Given** a listed version that is superseded, **When** the user follows it, **Then** they
   reach the page of that superseded version and not of the current one.
5. **Given** two users who accepted different documents, **When** either opens the page, **Then**
   they see only their own acceptances.
6. **Given** a user with no acceptances, **When** they open the page, **Then** it loads, lists
   nothing, and says there is nothing to show yet.
7. **Given** a visitor who is not signed in, **When** they request the page, **Then** they are
   sent to sign in and see no records.
8. **Given** a user who accepted a version of a document that is now a notice, **When** they open
   the page, **Then** that document is not listed.
9. **Given** a document with a version in force that the user has never accepted any version of,
   **When** they open the page, **Then** that document is not listed.
10. **Given** a signed-in user anywhere in the account area, **When** they look at the area's
    menu, **Then** it has an entry leading to this page, and on this page that entry is marked as
    the current one.
11. **Given** a user who accepted more than four versions of one document, **When** they open the
    page, **Then** the three most recently published are shown, the others are on the page in a
    part the user opens in place, and that part says how many it holds.
12. **Given** a user who accepted four versions of one document or fewer, **When** they open the
    page, **Then** all of them are shown and nothing is held back.

---

### User Story 2 - Knowing a newer version is in force (Priority: P2)

A person accepted the terms when they signed up. The site has since published a new version, and
nothing has asked them to accept it yet. On the page, the terms entry tells them a newer version is
in force that they have not accepted, and links to it so they can read it. For the privacy policy,
where they accepted the version in force, the entry says nothing of the kind.

**Why this priority**: Without it the list could mislead. A person would read "agreed to the terms"
and take it to mean the terms as they stand today.

**Independent Test**: For one user, accept the version in force of one document and only a
superseded version of another. Open the page and check that only the second document carries the
statement, and that its link leads to the version in force.

**Acceptance Scenarios**:

1. **Given** a user whose most recent acceptance of a document is of a superseded version,
   **When** they open the page, **Then** the document's entry states that a newer version is in
   force that they have not accepted, and links to the version in force.
2. **Given** a user who accepted the current version of a document, **When** they open the page,
   **Then** that document's entry carries no such statement.
3. **Given** a user who accepted the current version and earlier ones, **When** they open the
   page, **Then** the earlier versions are listed and the entry still carries no such statement.
4. **Given** a document's entry that states a newer version is in force, **When** the user looks
   for a way to accept it on this page, **Then** there is none.
5. **Given** a new version is published after the user last opened the page, **When** they open
   it again, **Then** the entry now carries the statement, with nothing done by the user or the
   project in between.

---

### User Story 3 - A project that leaves part of it out (Priority: P3)

A developer installs the package. One project mounts the account area and the package's pages, and
the list appears in the account area with nothing more to configure. Another project has no
account area at all. It uses the package to publish documents and record acceptances, and that
keeps working: nothing fails at start-up, nothing fails when a page is rendered, and no link
points at a page that is not there.

**Why this priority**: The account area is optional in django-mvp, and the package must not turn
it into a requirement. This is a guarantee for developers and not something a person using the
site sees.

**Independent Test**: Run the package's existing behaviour in a project that does not mount the
account area, and check that the system checks pass and that document pages render. Then mount the
area and check the entry and the page appear without further configuration.

**Acceptance Scenarios**:

1. **Given** a project that mounts both the account area and the package's pages, **When** a
   signed-in user opens the account area, **Then** the entry and the page are there with no
   setting changed.
2. **Given** a project that does not mount the account area, **When** it starts and serves
   document pages, **Then** nothing fails and no page links to the list.
3. **Given** a project that does not mount the package's pages, **When** a signed-in user opens
   the account area, **Then** the area's menu has no entry for the list and nothing fails.
4. **Given** a compliance editor naming a new document, **When** they choose a slug that would
   give the document the same address as the list, **Then** the slug is refused.

---

### Edge Cases

- A person accepted versions 2025.1 and 2026.2 of a document and never accepted 2026.1. The entry
  lists the two they accepted and nothing else.
- A document a person agreed to is made a notice, then made a document people agree to again. It
  disappears from the list and returns, with the same acceptances, because none was touched.
- A person accepted a version, and the document's name was changed afterwards. The entry carries
  the document's present name. The wording behind each link is what was published.
- A person has acceptances of many versions across many documents. The page shows all of them.
- Two people share a browser one after the other. The second sees only their own acceptances,
  because the page is built from who is signed in and nothing in the address names a person.
- An address is tried with another user's identifier added to it. There is no such address: the
  page takes no identifier.
- A staff user opens the page. They see their own acceptances, like anyone else. Other people's
  records stay behind the FS-004 page and its permission.
- A person opens their own list. No record of a disclosure is written, because nothing was
  produced about them for anybody else.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST provide a page, for a signed-in user, that lists every document
  they hold at least one acceptance for and that is a document people agree to. *(US-1)*
- **FR-002**: Under each listed document the page MUST list every version of it the user accepted,
  each with its version number and the date of the acceptance, ordered with the most recently
  published version first. *(US-1)*
- **FR-003**: Each listed version MUST link to the page that serves that exact version, whether
  it is current or superseded. *(US-1)*
- **FR-004**: The page MUST show only the acceptances of the user who is signed in. It MUST take
  no parameter that selects a person, and no user, staff included, may reach another person's
  list through it. *(US-1)*
- **FR-005**: A visitor who is not signed in MUST be sent to sign in and MUST be shown no record.
  *(US-1)*
- **FR-006**: A notice MUST NOT be listed, including one the user accepted a version of before it
  became a notice. *(US-1)*
- **FR-007**: A document the user holds no acceptance for MUST NOT be listed. *(US-1)*
- **FR-008**: A user with nothing to list MUST get the page, with a statement that there is
  nothing to show yet. *(US-1)*
- **FR-009**: A listed document whose current version the user has not accepted MUST state that a
  newer version is in force that they have not accepted, and MUST link to the version in force. A
  listed document whose current version the user has accepted MUST NOT. *(US-2)*
- **FR-010**: The page MUST offer no way to accept a version, and no way to edit, withdraw or
  delete an acceptance. *(US-2)*
- **FR-011**: The account area's menu MUST carry an entry for the page for a signed-in user, and
  the page MUST be presented as part of the account area, with that entry marked as current.
  *(US-1, US-3)*
- **FR-012**: The entry and the page MUST be present without any setting once a project mounts
  both the account area and the package's pages. *(US-3)*
- **FR-013**: In a project that mounts only one of the two, or neither, the package MUST start,
  pass its system checks and serve everything it served before, and MUST render no link to the
  list that leads nowhere. *(US-3)*
- **FR-014**: No document may take a slug that gives it the address of the list, and the list's
  address MUST never answer with a document. *(US-3)*
- **FR-015**: Building the page MUST cost a number of database queries that does not grow with
  the number of documents, versions or acceptances listed. *(US-1, US-2)*
- **FR-016**: Opening the page MUST write nothing: no acceptance, no record of a disclosure, and
  no change to any document or version. *(US-1)*
- **FR-017**: Every user-facing string this feature adds MUST be translatable, and none may state
  or imply that the person or the site is compliant. *(US-1, US-2)*
- **FR-018**: The documentation MUST explain what the page shows, what a project mounts for it to
  appear, and that it is left out safely when the account area is absent. *(US-3)*

- **FR-019**: A listed document with more than four accepted versions MUST show the three most
  recently published and hold the others, still on the page, in a part the user opens in place,
  stating how many it holds. With four or fewer, all are shown. *(US-1; added 2026-10-01)*

### Key Entities

- **Acceptance** (FS-003): unchanged, and read only. The page reads the user's acceptances through
  the same identity the records were written under.
- **Version** (FS-001, FS-006): unchanged. Each listed version is reached at the address FS-006
  gave it.
- **Document** (FS-001, FS-007): unchanged, apart from one more slug that cannot be taken. Its
  kind decides whether it can be listed, and its current version decides whether the entry says a
  newer version is in force.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any user, the versions listed are exactly the versions that user accepted of
  documents people agree to: none missing, none added, and none belonging to another user.
- **SC-002**: Every listed version leads to the wording that user accepted, word for word.
- **SC-003**: A document's entry says a newer version is in force exactly when the user has not
  accepted its current version.
- **SC-004**: A signed-in person reaches the page from the account area's landing page in one
  step.
- **SC-005**: The number of database queries for the page is the same for a user with one
  acceptance as for a user with fifty across ten documents.
- **SC-006**: A project that already mounts the account area and the package's pages gets the
  page by upgrading, with no change to its settings, addresses or templates.
- **SC-007**: A project without the account area upgrades with no change in behaviour.

## Clarifications

### Session 2026-10-01

- **Q**: Is the list one line per acceptance, or one entry per document? → **A**: One entry per
  document with the accepted versions under it (FR-001, FR-002). The question a person brings is
  "what did I agree to about the terms", and whether a newer version is in force is a fact about
  the document, not about one acceptance. A flat log would repeat that statement on every line or
  leave the reader to work out which line it belongs to.
- **Q**: Does a document appear when the person accepted a version of it and it has since been
  made a notice? → **A**: No (FR-006). FS-007 settled that a notice's page stops saying the reader
  agreed, because a page describes the document as it now stands. The list follows the same rule.
  The acceptance is untouched, is still produced by the FS-004 page, and the document returns to
  the list if its kind is changed back.
- **Q**: In what order are documents and versions listed? → **A**: Versions by publication, newest
  first (FR-002), so the version nearest to what is in force is read first. Documents follow the
  order the package already lists documents in on a document page, so a person meets them in the
  same order in both places.
- **Q**: What does a project have to mount for the page to exist? → **A**: The account area and the
  package's own pages (FR-012). Every listed version links to a page the package serves, so a
  list in a project that serves none of those pages would be a list of dead links. With either
  missing, the entry and the page are absent and nothing else changes (FR-013).
- **Q**: Does a person reading their own list count as their records being produced, which FS-004
  records each time? → **A**: No (FR-016). That record exists so a site can say who looked at whose
  records. A person reading their own is not that, and writing a row on every page view would add
  personal data about ordinary browsing.

## Assumptions

- FS-001 to FS-007 are delivered, and this spec is written against them as they stand on main:
  acceptances are recorded from code and read back per person, each published version has a page
  at its own address, and a document is either one people agree to or a notice.
- django-mvp provides the account area, with a menu an installed package can add an entry to and
  a layout a contributed page can use. The area is optional for a project.
- The flow that asks a user to accept documents (R4) is not built. When it is, it may link from
  this page. This feature leaves no placeholder for it.
- A person's acceptances are matched to them the way FS-003 writes them, so a project that changed
  how acceptances are tied to an account sees the list follow that choice.
- The page shows a person's acceptances to that person only and stores nothing new, so Article XIV
  does not apply.
- The list is not paginated. A long history is folded in place (FR-019). It is bounded by the
  number of documents a site publishes and the versions of each that one person accepted.
