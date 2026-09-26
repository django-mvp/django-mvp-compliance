# Feature Specification: Documents and their versions readable as pages of the site

**Feature Branch**: `006-documents-readable-as-pages`

**Created**: 2026-09-26

**Status**: Draft

**Serves**: G1, G5 · **Roadmap**: R2 · **Issue**: #58

**Input**: A published document only counts as published if somebody can read it, and at the moment
nobody can: the wording exists only in the admin. People usually reach a privacy policy or terms of
use from a link in a site's footer, often before they have an account, and they expect that address
to keep working and to show whatever is in force now. Someone who agreed to an earlier wording also
needs to be able to go back and read exactly that wording long after it was replaced, so every
version needs a permanent address of its own. The pages should look like the rest of the site they
are installed in without the project writing any templates, and a project that wants them to look
different should be able to change that without forking the package.

## Scope

Anyone reading the site, signed in or not, can read published documents as ordinary pages of the
host site. There are four kinds of page:

- **The document's page** has one permanent address per document and always shows the version in
  force. This is the address a footer links to.
- **A version's page** has one permanent address per published version, and keeps it after the
  version is superseded.
- **A document's version list** shows every version of the document that has been published, with
  the dates each one was in force.
- **The document index** lists every document that has a version in force. A project can link to it
  from its footer as a single "Legal" link.

Every page serves the HTML stored when the version was published. The pages take their layout,
navigation and theme from the django-mvp shell the site already uses. The project mounts the
package's addresses under a prefix of its choosing and writes no templates. To change how the pages
look, the project overrides the package's templates.

To give a document an address that survives a change to its name, each document gains a short
identifier, its **slug**. The slug can be changed until the document's first version is published,
and never after that.

Asking anybody to agree to what they read, and stopping them until they do, belong to R4 and R5.
Documents in more than one language belong to R7. An email to the site's users about a new version
is issue #42, which will link to these pages but is not part of this feature. The package adds
nothing to the host project's menus. Where the links go is the project's decision.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reading the document in force (Priority: P1)

A visitor follows the "Privacy policy" link in a site's footer. They may never have signed in. They
land on a page that looks like the rest of the site and shows the privacy policy currently in force,
with its version number and the date it came into force. The link in the footer never has to
change: when a new version is published, the same address shows it.

A developer gets there by installing the package, adding its addresses to the project's URLs and
linking to them. They write no templates.

**Why this priority**: It is the feature. A document nobody can read is not published in any sense
that matters, and R4 needs this page before it can ask anyone to agree to it.

**Independent Test**: Publish a version of a document in the demo, open the document's address
without signing in, and confirm the page shows that version's stored HTML inside the site's own
layout. Publish a second version and confirm the same address now shows the second.

**Acceptance Scenarios**:

1. **Given** a document with a version in force, **When** a visitor who is not signed in opens the
   document's address, **Then** the page shows that version's wording.
2. **Given** that page, **When** it is read, **Then** it names the document, the version's number
   and the date the version came into force.
3. **Given** that page, **When** it is served, **Then** the wording is the HTML stored at
   publication, byte for byte, and not a fresh rendering of the Markdown.
4. **Given** a project using the django-mvp shell that has written no templates for this package,
   **When** the page is served, **Then** it carries the shell's layout, navigation and theme.
5. **Given** a document whose version in force is replaced by a newly published one, **When** the
   same address is opened again, **Then** it shows the new version.
6. **Given** a document that has only drafts, **When** its address is opened, **Then** the response
   is "not found".
7. **Given** an address naming no document, **When** it is opened, **Then** the response is "not
   found".
8. **Given** a signed-in member of staff, **When** they open the address of a document that has only
   drafts, **Then** the response is still "not found". Drafts are previewed in the admin.

---

### User Story 2 - Reading any version at its own address (Priority: P1)

A person agreed to the terms two years ago and wants to see what they agreed to. The terms have been
reworded twice since. The version they accepted still has its own address, and that page shows
exactly the wording they were served, with a clear statement that it has been replaced and a link
to the terms in force today.

The version in force has an address of its own too, so a link to "the terms as they stand today"
and a link to "version 2026.2 of the terms" are different links. Only the second keeps showing the
same words for ever.

**Why this priority**: G2 depends on it. An acceptance is only evidence if the person can go back and
read what they accepted, and superseded wording that cannot be reached is gone as far as a reader is
concerned.

**Independent Test**: Publish two versions of a document. Open the first version's address and
confirm it shows the first wording, says it has been replaced and links to the document's page. Open
the second version's address and confirm it shows the second wording and says it is in force.

**Acceptance Scenarios**:

1. **Given** a published version, current or superseded, **When** a visitor who is not signed in
   opens its address, **Then** the page shows that version's stored HTML.
2. **Given** a superseded version's page, **When** it is read, **Then** it says the version has been
   replaced, gives the dates it was in force, and links to the document's page.
3. **Given** the version in force, **When** its own address is opened, **Then** the page shows the
   same wording as the document's page and says it is the version in force.
4. **Given** a version that is later superseded, **When** its address is opened afterwards, **Then**
   it is the same address as before, and it shows the same wording.
5. **Given** a draft, **When** any address that would name it is tried, **Then** the response is "not
   found". A draft has no number, so no address names it.
6. **Given** a version number that belongs to a different document, **When** it is opened under this
   document's address, **Then** the response is "not found".
7. **Given** a version's page, **When** it is served, **Then** it carries the shell's layout,
   navigation and theme, as the document's page does.

---

### User Story 3 - Finding a document and its earlier versions (Priority: P2)

A reader who knows a document was reworded, but has no link to the old wording, can still find it.
The document's page links to a list of every version that has been published. The list shows each
version's number and the dates it was in force, marks the one in force now, and links to each
version's page.

A site that publishes several documents usually wants a single "Legal" link in its footer rather
than one link per document. The document index gives it one address listing every document that has
a version in force, each linking to its page.

**Why this priority**: The version addresses from US-2 work without it, but only for someone who
already has the link. This makes them findable. The index saves each project building the same
list.

**Independent Test**: Publish three versions of one document and one version of another, and leave a
third document with only a draft. Open the first document's version list and confirm it shows all
three versions with their dates, newest first, the current one marked. Open the index and confirm it
lists the two documents that have a version in force and not the third.

**Acceptance Scenarios**:

1. **Given** a document's page, **When** it is read, **Then** it links to the document's version
   list.
2. **Given** a document with several published versions, **When** its version list is opened,
   **Then** it shows every published version, newest first, each with its number, the date it came
   into force, and the date it was replaced if it has been.
3. **Given** that list, **When** it is read, **Then** the version in force is marked as such, and
   every entry links to that version's page.
4. **Given** a document that has drafts as well as published versions, **When** its version list is
   opened, **Then** no draft appears.
5. **Given** documents with a version in force and documents with only drafts, **When** the index is
   opened, **Then** it lists every document that has a version in force, each linking to its page,
   and no other document.
6. **Given** no document has a version in force, **When** the index is opened, **Then** it says there
   is nothing published yet, rather than showing an empty list.
7. **Given** the version list or the index, **When** it is served, **Then** it carries the shell's
   layout, navigation and theme.

---

### User Story 4 - A stable address, and a project's own presentation (Priority: P2)

The slug is chosen when the document is created, and the admin suggests one from the name. Until the
document's first version is published nobody can have linked to it, so the slug can still be
corrected. Once a version is published the slug is fixed. Renaming "Terms" to "Terms of use"
afterwards changes what the page is called, not where it lives.

A project whose design needs these pages to look different overrides the package's templates in the
usual Django way, by putting a template of the same name in its own templates directory, without
forking the package or changing any setting. The documentation names each template and what it is
given.

**Why this priority**: The stable address is what US-1's footer link rests on, but a document
published without ever being renamed shows none of this. The override is an escape hatch that most
projects never need.

**Independent Test**: Create a document, correct its slug, publish a version, and confirm the slug can
no longer be changed through the admin or from code while the name still can. Put an override of the
document page's template in the demo's templates and confirm it is used.

**Acceptance Scenarios**:

1. **Given** a new document being created in the admin, **When** its name is typed, **Then** a slug
   is suggested from the name and can be edited before saving.
2. **Given** a document with no published version, **When** its slug is changed, **Then** the change
   is saved.
3. **Given** a document with a published version, **When** anything tries to change its slug through
   the admin or from code, **Then** it is refused.
4. **Given** a document with a published version, **When** its name is changed, **Then** the change
   is saved, and the document's page and every version's page keep their addresses and show the new
   name.
5. **Given** two documents, **When** the second is given the first's slug, **Then** it is refused.
6. **Given** a project template at the same path as one of the package's page templates, **When**
   that page is served, **Then** the project's template is used.
7. **Given** the documentation, **When** a developer reads it, **Then** it shows how to mount the
   addresses, how to link to a document's page from a template, and which templates can be
   overridden.

---

### Edge Cases

- A version's stored HTML begins with a heading of its own that repeats the document's name. The
  page still serves the stored HTML unaltered.
- A document's name contains characters that look like markup. The page shows the name as written,
  escaped, never as markup.
- Two versions of a document are published in one year. Their numbers, such as 2026.1 and 2026.2,
  are both valid in an address, and each opens its own version.
- A document created before this feature has no slug. Upgrading gives it one derived from its name,
  and a clash between two derived slugs is resolved so that both documents keep an address. No
  document or version is dropped.
- A superseded version is opened after the document's version in force has itself been replaced
  twice. It still links to the document's page, which shows whatever is in force now.
- The host project mounts the package's addresses under a prefix of its own. Links between the
  package's pages still resolve.
- A signed-in user who has not accepted the version in force opens the document's page. They read it
  like anyone else. Asking them to agree is R4.
- A version's HTML contains a link. It is served as stored, and the sanitiser already applied at
  publication decides what survived.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each document MUST have a page at a permanent address, built from its slug, that shows
  the version in force. *(US-1)*
- **FR-002**: Each published version, current or superseded, MUST have a page at a permanent address
  built from its document's slug and its number. *(US-2)*
- **FR-003**: Each document MUST have a version list at its own address, showing every published
  version newest first, with its number, the date it came into force, and the date it was replaced
  if it has been, and marking the version in force. *(US-3)*
- **FR-004**: The package MUST provide a document index at its own address, listing every document
  that has a version in force and linking to each document's page. *(US-3)*
- **FR-005**: Every page this feature adds MUST be readable by any visitor, signed in or not, with
  no permission required. *(US-1, US-2, US-3)*
- **FR-006**: A page MUST serve the version's HTML exactly as stored at publication, and MUST NOT
  render Markdown when it is requested. *(US-1, US-2)*
- **FR-007**: A draft MUST NOT be shown or listed on any page this feature adds, to anyone. A document
  with nothing in force MUST answer "not found" at its page and version list, and MUST NOT appear in
  the index. *(US-1, US-2, US-3)*
- **FR-008**: An address naming no document, or a number that is not a published version of the
  named document, MUST answer "not found". *(US-1, US-2)*
- **FR-009**: The document's page and each version's page MUST name the document, the version's
  number and the date it came into force. *(US-1, US-2)*
- **FR-010**: A superseded version's page MUST say it has been replaced, give the dates it was in
  force, and link to the document's page. The page of the version in force MUST say it is in force.
  *(US-2)*
- **FR-011**: The document's page MUST link to the document's version list. *(US-3)*
- **FR-012**: Every page this feature adds MUST render within the django-mvp shell, taking its
  layout, navigation and theme from the host project, with no template written by the project.
  *(US-1, US-2, US-3)*
- **FR-013**: The package MUST provide its addresses as one set the host project mounts under a
  prefix of its choosing, and each page MUST be reachable by name so that a project can link to it
  from its own templates. *(US-1, US-4)*
- **FR-014**: The package MUST NOT add anything to the host project's menus or navigation. *(US-4)*
- **FR-015**: Each document MUST have a slug, unique across documents, made of lowercase letters,
  digits and hyphens. *(US-4)*
- **FR-016**: The admin MUST suggest a slug from the document's name when a document is created, and
  let it be edited. *(US-4)*
- **FR-017**: A document's slug MUST be refused any change once the document has a published
  version, by every route that refuses other changes to published content. Its name MUST stay
  editable. *(US-4)*
- **FR-018**: Upgrading MUST give every existing document a slug derived from its name, keep every
  document and version, and resolve a clash between derived slugs without refusing the upgrade.
  *(US-4)*
- **FR-019**: A project template at the same path as one of the package's page templates MUST
  replace it, with no setting required. *(US-4)*
- **FR-020**: Every user-facing string on the pages MUST be translatable, and the pages MUST render
  in the language active when they are requested. *(US-1, US-2, US-3)*
- **FR-021**: Nothing this feature adds MAY claim that publishing a document makes a site compliant,
  or name a regulation. *(US-1)*
- **FR-022**: The documentation MUST show how to mount the addresses, how to link to a document's
  page and the index from a template, and list each page template with what it is given. *(US-4)*
- **FR-023**: The glossary MUST define *Slug* as the document's identifier in its address, fixed once
  a version is published. *(US-4)*

### Key Entities

- **Document** (FS-001): gains its slug, the identifier in every address the document and its
  versions have. Fixed once the document has a published version.
- **Version** (FS-001, FS-002): unchanged. Its number and the dates it was in force identify it on
  the page.
- **Document's page**, **version's page**, **version list** and **document index**: read-only views
  of published data. Nothing about them is stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the demo, which writes no template for this package, every page this feature adds
  renders inside the django-mvp shell.
- **SC-002**: For every published version, the wording on its page is byte-for-byte the stored HTML.
- **SC-003**: For every draft, no page this feature adds shows it or lists it, whether the visitor is
  anonymous, a signed-in user or staff.
- **SC-004**: After a new version is published, the document's page shows it, and every earlier
  version's address still answers with the wording it answered with before.
- **SC-005**: Once a document has a published version, no route that refuses other changes to
  published content accepts a change to its slug.
- **SC-006**: The number of database queries for a document's page, version list and the index does
  not grow with the number of versions or documents.
- **SC-007**: A developer can make the pages reachable and link to a document from the site's footer
  with one line in the project's URLs and one link in a template.
- **SC-008**: `makemessages` over the package picks up every string on the pages.

## Clarifications

### Session 2026-09-26

- **Q**: Can a document's slug change? → **A**: Until the document's first version is published,
  yes. After that, never (FR-017). No address exists before publication, so nobody can have linked
  to it, and correcting a typo in the slug costs nothing. After publication the address is the
  whole point, and a changed slug breaks every footer link and every link already sent to someone.
- **Q**: Do members of staff see drafts on the public pages? → **A**: No (FR-007). The admin already
  previews drafts. A public page that looks different depending on who is signed in makes "what does
  the site say today" harder to answer, and a member of staff could mistake a draft for the version
  in force.
- **Q**: Where does the list of a document's versions live? → **A**: At its own address, linked from
  the document's page (FR-003, FR-011). The document's page is what a footer links to, so it should
  be the wording itself. A history list under a long legal text is hard to find.
- **Q**: What does a superseded version's page link to: the version that replaced it, or the version
  in force? → **A**: The document's page (FR-010), which always shows the version in force. After two
  rewordings, the version that directly replaced it is superseded too, and "the next one" would send
  the reader to another old page.
- **Q**: Does the index include a document with only drafts? → **A**: No (FR-004). Its page answers
  "not found", so listing it would give the reader a dead link.

## Assumptions

- FS-001, FS-002 and FS-005 are delivered, and this spec is written against them as they stand on
  main: a version is numbered when it is published, and at most one version per document is in
  force.
- The date a version came into force is its moment of publication. The date it was replaced is the
  moment the next version of the document was published.
- Nothing has been released, so documents without a slug exist only in development databases.
  Upgrading still carries them forward under Article XVI.
- The host project uses the django-mvp shell, which the package already depends on. How the pages
  plug into it is a planning question.
- The package ships an English catalog only, as for every other string.
- The slug is not personal data, so Article XV does not apply.
