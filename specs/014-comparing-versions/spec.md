# Feature Specification: Comparing two versions of a document

**Feature Branch**: `014-comparing-versions`

**Created**: 2026-10-26

**Status**: Draft

**Serves**: G3 · **Roadmap**: R6 · **Issue**: #133

**Input**: A summary says what whoever prepared a version chose to say about it, not exactly what
changed. A reader who wants to know precisely how two versions of a document differ, whether the
one they agreed to and the one now in force or any two published versions, should be able to see
them compared, with what was added and what was removed marked in the text. A summary only covers
one step, so a person who last agreed two versions ago has nothing that shows everything that
changed since, and a comparison does. It also lets anyone looking at a person's record see exactly
how the version they agreed to differs from the one in force today.

## Scope

Anyone reading the site can compare two published versions of the same document. The comparison
shows one text, with the words added since the older version and the words removed from it marked
where they occur, and names both versions with their numbers and the dates they came into force.
It has a permanent address, built from the document and the two versions, that keeps showing the
same comparison for ever, because both versions are published and never change.

A reader reaches a comparison without typing an address:

- **From any document page** (FS-006), by choosing another published version to compare with the
  one being read. A superseded version offers its comparison with the version in force directly.
- **From the account area's list of what a person has agreed to** (FS-008), where a document says
  a newer version is in force that the person has not accepted. It offers the comparison between
  the newest version they accepted and the version in force.
- **From the page asking a person to agree** (FS-009), for a document the person agreed to an
  earlier version of. It offers the same comparison. A person agreeing to a document for the first
  time is offered none.
- **From the page staff use to produce everything held about a person** (FS-004), for each
  acceptance of a version that is no longer in force. It offers the comparison between that version
  and the version in force.

A developer can link to a comparison from the project's own templates and messages by the page's
name, and can replace its template as for every other page the package serves.

Some things stay out of this feature:

- The short summary of what changed, written by whoever prepares a version and shown when a person
  is asked to agree again, is issue #132. This feature neither shows it nor depends on it.
- Drafts are never compared, on these pages or anywhere else this feature adds. A draft is visible
  only to the people who manage documents, and it is previewed in the admin.
- Only versions of the same document are compared. Two different documents are never compared with
  each other.
- The copy a person downloads (FS-012) is unchanged. It carries no comparison.
- Emailing people about a new version is issue #42. It may link to a comparison once both exist,
  but that link is not part of this feature.
- What counts as outstanding, what an acceptance holds and when a person is asked to agree are
  unchanged.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comparing any two published versions of a document (Priority: P1)

A reader is looking at the terms of a site, version 2026.3. They remember reading 2026.1 and want to
know exactly what is different now. From the terms' page they choose to compare with 2026.1. They
see one text with the words added since 2026.1 marked as added and the words taken out marked as
removed, in the places they occur, with both versions named. A one-word change in a long paragraph
marks that word, not the whole paragraph. From the comparison they can open either version on its
own page. They copy the address and send it to a colleague, who sees the same comparison.

A reader on the page of a superseded version is offered its comparison with the version in force,
since "what is different now" is the question that version's page most often raises.

**Why this priority**: It is the feature. Every other way into a comparison in this spec leads to
this one, and it is the only one open to a reader who is not signed in.

**Independent Test**: Publish three versions of a document, each changing some words of the one
before. Without signing in, open the document's page, choose to compare the version in force with
the first version, and check that the comparison names both versions, marks each word added and
each word removed between them and nothing else, and links to both versions' pages. Open the same
address again after publishing a fourth version and check it shows the same comparison.

**Acceptance Scenarios**:

1. **Given** a document with two or more published versions, **When** a visitor who is not signed
   in reads any version on the document's page, **Then** they can choose any other published
   version of the document to compare it with, without typing an address.
2. **Given** a comparison of two published versions, **When** it is read, **Then** every word that
   is in the newer version and not the older is marked as added, every word that is in the older
   version and not the newer is marked as removed, each where it occurs in the text, and no word
   that both versions share is marked.
3. **Given** two versions that differ by one word in a long paragraph, **When** they are compared,
   **Then** that word is marked and the rest of the paragraph is not.
4. **Given** a comparison, **When** it is read, **Then** it names the document and both versions,
   each with its number and the date it came into force, says which is the older and which the
   newer, and links to each version's own page.
5. **Given** a comparison asked for with the newer version first, **When** it is shown, **Then** it
   is the same comparison as with the older version first: what was added is always what the newer
   version has and the older lacks.
6. **Given** a superseded version on the document's page, **When** it is read, **Then** the
   comparison of that version with the version in force is offered directly.
7. **Given** a document with a single published version, **When** its page is read, **Then** no
   comparison is offered.
8. **Given** a comparison's address, **When** it is opened again after newer versions of the
   document have been published, **Then** it shows the same comparison as before.
9. **Given** a version compared with itself, or two versions whose wording is identical, **When**
   the comparison is opened, **Then** it says that the two have no differences and marks nothing.
10. **Given** a comparison's address naming a draft, a version of another document, a version that
    does not exist, or a document that does not exist, **When** it is opened, **Then** the response
    is "not found", whoever asks, staff included.
11. **Given** two versions whose differences include a heading, a list item or a link, **When** they
    are compared, **Then** the structure of the text survives in the comparison, and the change is
    marked within it.
12. **Given** a comparison, **When** it is read with assistive technology or without colour, **Then**
    what was added and what was removed can still be told apart.

---

### User Story 2 - Seeing what changed since I last agreed (Priority: P1)

A person agreed to a site's privacy policy, version 2025.2. Two versions have been published since.
In the account area, their list of what they have agreed to says a newer version is in force. Beside
it they can open the comparison between 2025.2, the newest version they accepted, and the version in
force: everything that changed since they agreed, in one text, rather than two separate steps. When
the site next asks them to agree to the privacy policy, the page asking offers the same comparison
beside the version they are asked about.

A person who has never agreed to a document is asked about it as before, with no comparison, because
they have nothing earlier to compare with.

**Why this priority**: It is the case the request names: a summary covers one step, and a person who
last agreed several versions ago has nothing else that shows them everything that changed. It is
what makes agreeing again an informed decision rather than a click (G3).

**Independent Test**: Publish three versions of a document. As a user who accepted only the first,
open the account area's list and check the document offers the comparison between the first version
and the third, and that it shows every change across both steps. Open the page asking to agree and
check the same comparison is offered for that document. As a user who has accepted nothing, open the
page asking to agree and check no comparison is offered.

**Acceptance Scenarios**:

1. **Given** a signed-in user whose newest accepted version of a document is no longer in force,
   **When** they open the account area's list of what they have agreed to, **Then** that document
   offers the comparison between the newest version they accepted and the version in force.
2. **Given** a user who accepted a document's version in force, **When** they open the same list,
   **Then** that document offers no comparison.
3. **Given** a user who accepted versions 1 and 2 of a document while version 4 is in force, **When**
   the comparison is offered, **Then** it compares version 2 with version 4.
4. **Given** a user with a document outstanding who accepted an earlier version of it, **When** they
   open the page asking them to agree, **Then** that document offers the comparison between the
   newest version they accepted and the version they are asked about.
5. **Given** a user with a document outstanding who has never accepted any version of it, **When**
   they open the page asking them to agree, **Then** that document offers no comparison.
6. **Given** a user who opens a comparison from the page asking them to agree, **When** they return
   to that page, **Then** it still has the destination they were heading for, and opening the
   comparison has recorded nothing.
7. **Given** a user with several outstanding documents, some agreed before and some not, **When**
   they open the page asking them to agree, **Then** each document agreed before offers its own
   comparison and the others offer none, and the number of database queries to show the page does
   not grow with the number of documents.
8. **Given** a comparison reached from the account area or the page asking to agree, **When** it is
   opened, **Then** it is the same comparison, at the same address, that any visitor reaches for
   those two versions.

---

### User Story 3 - Seeing how what a person agreed to differs from what is in force today (Priority: P2)

Somebody fielding a request about a named person produces everything the package holds about them.
One of the person's acceptances is of a version of the terms that has since been replaced. Beside
that acceptance they can open the comparison between the version the person agreed to and the
version in force, to see exactly what the person has and has not agreed to.

**Why this priority**: It answers the question a dispute about an old acceptance usually turns on.
It is less common than a person asking about their own record, and the comparison it opens is the
one from US-1.

**Independent Test**: Record an acceptance of the first of two published versions for a user. As
staff, produce everything held about that user and check the acceptance offers the comparison
between the first version and the second. Record an acceptance of the second version and check
that acceptance offers none.

**Acceptance Scenarios**:

1. **Given** an acceptance of a version that is no longer in force, **When** staff produce
   everything held about that person, **Then** that acceptance offers the comparison between the
   version accepted and the version in force.
2. **Given** an acceptance of the version in force, **When** the same is produced, **Then** it
   offers no comparison.
3. **Given** a document whose version in force has been replaced since the acceptance was recorded,
   **When** the comparison is offered, **Then** it compares with whatever is in force when it is
   produced.
4. **Given** what is produced, **When** it is read, **Then** the wording served at the time of each
   acceptance is shown as before, unchanged by this feature.

---

### User Story 4 - Linking to a comparison from the project's own pages (Priority: P3)

A developer is writing the email their site sends when the terms change. They link from it to the
comparison between the previous version and the new one, by the page's name and the two version
numbers, without building the address by hand. A developer whose design needs the comparison to look
different replaces its template in the usual Django way, and the comparison is still produced the
same.

**Why this priority**: The pages in US-1 to US-3 already link to comparisons. This is for projects
that want to link from somewhere the package does not reach, which most will not need on day one.

**Independent Test**: In a template in the demo, link to a comparison by the page's name with a
document's slug and two version numbers, and check the link opens that comparison. Put a template of
the same name in the demo's templates and check it is used.

**Acceptance Scenarios**:

1. **Given** a document's slug and two version numbers, **When** a developer links to the comparison
   by the page's name, **Then** the link opens that comparison.
2. **Given** a project that mounts the package's pages and has written no template for the
   comparison, **When** it is opened, **Then** it renders inside the project's django-mvp shell.
3. **Given** a project template at the same path as the comparison's template, **When** the
   comparison is opened, **Then** the project's template is used, and it is given both versions and
   the marked-up text.
4. **Given** the documentation, **When** a developer reads it, **Then** it shows how to link to a
   comparison, what its address is built from, and what its template is given.

---

### Edge Cases

- A version's stored HTML contains markup that the sanitiser allowed. The comparison contains
  nothing beyond what the two stored versions contain, apart from the marks for what was added and
  removed.
- A document's wording contains text that looks like markup, written as text. It stays text in the
  comparison and is never turned into markup.
- Two versions differ only in whitespace or line breaks in the stored HTML, with the same words.
  The comparison marks nothing.
- A paragraph is moved from one place to another. It is shown removed where it was and added where
  it is now.
- Two versions are long, such as a full set of terms. The comparison still answers promptly
  (SC-004).
- A document's version in force is replaced while a person has its comparison open. The
  comparison they are reading does not change. The offer on the account area or the page asking to
  agree compares with the new version in force the next time either is opened.
- A document is a notice. Its versions are compared on its page like any other document's. It never
  appears on the account area's list or the page asking to agree, so nothing is offered there.
- A user accepted version 1 of a document, and versions 2 and 3 have been published since. The
  comparison offered to them is version 1 against version 3, the version in force, never against
  version 2, which is superseded too.
- The site is shown in a language other than English. The comparison's own words are translated.
  The versions' wording is compared as stored.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST show a comparison of any two published versions of the same
  document, to any visitor, signed in or not, with no permission required. *(US-1)*
- **FR-002**: A comparison MUST mark every word the newer version has and the older lacks as added,
  and every word the older version has and the newer lacks as removed, each where it occurs in the
  text, and MUST NOT mark any word the two share. *(US-1)*
- **FR-003**: Changes MUST be marked word by word, so that a change to part of a paragraph marks
  only the words that changed. *(US-1)*
- **FR-004**: A comparison MUST keep the structure of the text it compares, such as headings,
  paragraphs, lists and links, and mark changes within it. *(US-1)*
- **FR-005**: A comparison MUST be built from the HTML stored for each version at publication, and
  MUST NOT render Markdown when it is requested. *(US-1)*
- **FR-006**: A comparison MUST contain nothing beyond what the two stored versions contain, apart
  from the marks for what was added and removed. *(US-1)*
- **FR-007**: A comparison MUST name the document and both versions, each with its number and the
  date it came into force, say which is the older and which the newer, and link to each version's
  page. *(US-1)*
- **FR-008**: A comparison MUST always treat the earlier-published version as the older, whichever
  order the two are given in. *(US-1)*
- **FR-009**: Each comparison MUST have a permanent address built from the document and the two
  versions, and MUST keep showing the same comparison at it for ever. *(US-1, US-4)*
- **FR-010**: A comparison of a version with itself, or of two versions with identical wording,
  MUST say that the two have no differences and mark nothing. *(US-1)*
- **FR-011**: A comparison address naming a draft, a version of another document, a version or a
  document that does not exist MUST answer "not found", to everyone, staff included. *(US-1)*
- **FR-012**: Every document page MUST let the reader compare the version being read with any other
  published version of the document, without typing an address, whenever the document has more
  than one. *(US-1)*
- **FR-013**: The page of a superseded version MUST offer its comparison with the version in force
  directly. *(US-1)*
- **FR-014**: What was added and what was removed MUST be distinguishable without colour and MUST
  be conveyed to assistive technology. *(US-1)*
- **FR-015**: In the account area's list of what a person has agreed to, a document whose newest
  accepted version is not the version in force MUST offer the comparison between that version and
  the version in force. Other documents MUST offer none. *(US-2)*
- **FR-016**: On the page asking a person to agree, a document the person accepted an earlier
  version of MUST offer the comparison between the newest version they accepted and the version
  they are asked about. A document they have never accepted MUST offer none. *(US-2)*
- **FR-017**: Opening a comparison from the page asking to agree MUST record nothing and MUST NOT
  lose the destination the person was heading for. *(US-2)*
- **FR-018**: Where staff produce everything held about a person, each acceptance of a version that
  is not the version in force MUST offer the comparison between that version and the version in
  force. Acceptances of the version in force MUST offer none. *(US-3)*
- **FR-019**: The newest version a person accepted MUST be read from their stored acceptances, and
  the version in force MUST be the one in force when the page offering the comparison is shown.
  *(US-2, US-3)*
- **FR-020**: Offering comparisons MUST NOT make the number of database queries on the account
  area's list, the page asking to agree or the page staff produce grow with the number of documents
  or acceptances shown. *(US-2, US-3)*
- **FR-021**: A comparison MUST render inside the host project's django-mvp shell without the
  project writing a template, and the project MUST be able to replace its template with its own.
  *(US-4)*
- **FR-022**: The comparison MUST be reachable by name so a project can link to it from its own
  templates and messages, and MUST be served with the package's other pages. No document may take a
  slug that gives it the comparison's address. *(US-4)*
- **FR-023**: Every user-facing string this feature adds MUST be translatable, and none may state or
  imply that a site or a person is compliant. *(US-1, US-2)*
- **FR-024**: A comparison MUST NOT be presented as the wording anybody agreed to. The version's own
  page remains the record of what was served. *(US-1, US-3)*
- **FR-025**: The documentation MUST explain what a comparison shows, where the package offers one,
  how to link to one, what its address is built from and how its template is replaced. *(US-4)*

### Key Entities

- **Version** (FS-001, FS-006): unchanged, and read only. Its stored HTML is what is compared, and
  its number and the date it came into force identify it in a comparison.
- **Acceptance** (FS-003): unchanged, and read only. The newest acceptance a person holds for a
  document chooses the older version in the comparison offered to them.
- **Comparison**: a read-only view of two published versions of one document. Nothing about it is
  stored. Both versions are immutable, so the same two always give the same comparison.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every pair of published versions of a document in the demo, every word that
  differs between them is marked in their comparison, and no word they share is.
- **SC-002**: A person who last agreed to a document several versions ago reaches, in one step from
  the account area or the page asking to agree, one comparison that shows every change since.
- **SC-003**: For every draft, no comparison includes it or offers it, whether the visitor is
  anonymous, a signed-in user or staff.
- **SC-004**: Comparing two versions of about 15,000 words each, differing throughout, answers within
  one second on the demo.
- **SC-005**: A comparison's address shows the same comparison before and after newer versions of
  the document are published.
- **SC-006**: The number of database queries for a comparison does not grow with the number of
  versions the document has, and offering comparisons adds none that grow with the number of
  documents on any page that offers them.
- **SC-007**: In the demo, which writes no template for this package, the comparison renders inside
  the django-mvp shell.
- **SC-008**: `makemessages` over the package picks up every string this feature adds.

## Clarifications

### Session 2026-10-26

- **Q**: Are drafts ever compared, for instance a draft against the version in force while it is
  being written? → **A**: No (FR-011). A draft is visible only to the people who manage documents,
  and every page this feature touches is read by people who must never see one. Comparing a draft
  in the admin preview is a separate need of the person writing it and is not this feature.
- **Q**: Which text is compared, the Markdown or the HTML? → **A**: The HTML stored at publication
  (FR-005). It is what a reader was served and what an acceptance is evidence of. Markdown is never
  rendered at request time.
- **Q**: How finely are changes marked: whole paragraphs, lines or words? → **A**: Words (FR-003).
  A legal change is often one word ("may" to "will"), and a paragraph marked as changed leaves the
  reader to find it.
- **Q**: When a person accepted several versions of a document, which one is compared with the
  version in force? → **A**: The newest one they accepted (FR-015, FR-016). It is the last wording
  they agreed to, so its comparison with the version in force is exactly what they have not agreed
  to.
- **Q**: Which version is "older" when the two are given in either order? → **A**: The one
  published first (FR-008). A comparison reads the same however it was asked for.
- **Q**: Who can see a comparison? → **A**: Anyone (FR-001). Both versions are already public on
  their own pages, and a comparison shows nothing that is not on them.
- **Q**: Is a comparison stored? → **A**: No. Both versions are immutable, so it can always be
  produced again with the same result, and nothing about it is evidence of anything.

## Assumptions

- FS-001 to FS-013 are delivered, and this spec is written against them as they stand on main:
  every published version has a page at the document's address with `?version=`, the account area
  lists what a person has agreed to, the page asking to agree lists what is outstanding, and staff
  can produce everything held about a person.
- The comparison of two versions is the same for every reader. Who is reading changes only which
  comparison is offered, never what it shows.
- The package ships an English catalog only, as for every other string.
- No personal data is added or kept. A comparison offered to a person is chosen from acceptances
  that already exist, so Article XIV asks for nothing further.
- How a comparison is laid out and how additions and removals are marked is settled on a prototype
  reviewed on screen before the implementation is planned, as is how a reader chooses the version
  to compare with. No requirement here fixes wording or appearance.
