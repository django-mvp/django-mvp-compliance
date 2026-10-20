# Feature Specification: Declaring the documents a site links to

**Feature Branch**: `011-declared-documents`

**Created**: 2026-10-20

**Status**: Draft

**Serves**: G6 · **Roadmap**: — · **Issue**: #112

**Input**: A site's templates link to its legal documents long before anyone has written them. A
footer links to the privacy policy and the terms, and every one of those links names a document by
its slug. Nothing ties that slug to anything. The document exists only once somebody creates it in
the admin, they can create it under a different slug or not at all, and every link the developer
wrote leads nowhere. A fresh database, in development, in a test run or on a new deployment, has no
documents at all, so there is nothing to build those pages against. A developer should be able to
say in the project's settings which documents the site relies on, by slug and name, and find them
in every environment from the moment its database is migrated.

## Scope

A developer lists, in the project's settings, the documents the site links to. Each entry is a slug
and a name. When the project's database is migrated, every listed document that does not exist yet
is created with that slug and name and with no version. From then on it is an ordinary document:
whoever manages the documents finds it in the admin, writes its first version and publishes it, and
its page appears at the address the developer already linked to.

A declared document with no version behaves as any such document does today. It has no page, it is
not among the documents listed beside a page, it is never outstanding and it stops nobody. A link to
its address leads to a page that is not found until a version is published, exactly as a link to
any unpublished document does now.

The declaration settles the slug and nothing else that lasts:

- The slug is fixed from the start. Code links to a declared document before anything is
  published, so its address cannot wait until the first publication to be fixed, as an undeclared
  document's does (ADR 0019).
- The name is only where the document starts. Whoever manages the documents can rename a declared
  document like any other, and changing the name in the settings later does not rename it.
- Kind and enforcement are never declared. A declared document starts as a document people agree
  to, enforced, the same as one created in the admin, and whoever manages the documents changes
  either when they choose. Whether people agree to a text, and whether they are stopped until they
  do, is their decision and not the developer's.

Some things stay out of this feature:

- Documents created in the admin, without a declaration, keep working exactly as they do now. A
  project that declares nothing sees no change.
- No wording comes from the declaration. Every word of a document is still written and published
  by whoever manages the documents, without a deploy (G1).
- How a template links to a document does not change. The address is built from the slug, as the
  pages already document (FS-006).
- Hiding a link until its document has a version in force is not part of this feature.
- What the admin shows about where each document stands is roadmap item R10.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declaring the documents a site links to (Priority: P1)

A developer building a footer adds the privacy policy, the terms of use and the impressum to the
project's settings, each with a slug and a name, and links to each one's address from the footer
template. They migrate the database and the three documents exist, with no version yet, in their
own development database, in the test database and later in production. Whoever manages the
documents opens the admin and finds all three waiting for their first version. Once each is
published, the footer's links lead to it with nothing else changed.

**Why this priority**: It is the feature. Without it a link to a document is a guess about a slug
someone may or may not create later.

**Independent Test**: In the demo, declare a document that does not exist, migrate, and confirm the
document exists with the declared slug and name, no version, and the same kind and enforcement as a
document created in the admin. Open its address and confirm it is not found. Publish a version in
the admin and confirm the same address now shows it. Migrate again and confirm nothing about the
document changed and no second one was created.

**Acceptance Scenarios**:

1. **Given** a project that declares a document whose slug no document has, **When** the database
   is migrated, **Then** a document exists with the declared slug and name, no version, and the
   kind and enforcement a document created in the admin starts with.
2. **Given** that declared document with no version, **When** anyone opens its address, **Then**
   the page is not found, it is not listed beside any other document's page, and it is outstanding
   for nobody.
3. **Given** that declared document, **When** a version of it is published, **Then** its address
   shows that version.
4. **Given** a declared document that already exists, **When** the database is migrated again,
   **Then** its name, kind, enforcement and versions are unchanged and no other document is
   created.
5. **Given** a document created in the admin before any declaration, **When** a developer declares
   its slug and the database is migrated, **Then** that document becomes the declared one, with its
   name, kind, enforcement, versions and acceptances unchanged.
6. **Given** a declared document whose name was changed in the admin, **When** the declared name is
   changed in the settings and the database is migrated, **Then** the document keeps the name it
   was given in the admin.
7. **Given** a declared document, **When** its declaration is removed from the settings and the
   database is migrated, **Then** the document, its versions and its acceptances remain.
8. **Given** a test run of a project that declares documents, **When** the test database is set
   up, **Then** every declared document exists in it.
9. **Given** a declaration whose name another document already has under a different slug,
   **When** the database is migrated, **Then** the project is told which declaration conflicts with
   which document, and that run creates no declared document.
10. **Given** a declaration whose slug is not one a document may have, such as one with capitals or
    one reserved for the package's own pages, **When** the database is migrated, **Then** the
    project is told which declaration is at fault, and that run creates no declared document.
11. **Given** a project that declares nothing, **When** the database is migrated, **Then** no
    document is created and none is changed.

---

### User Story 2 - Writing a document the site already links to (Priority: P2)

Whoever manages the documents opens a declared document in the admin to write its first version.
They can change its name, whether people agree to it and whether it is enforced, but not its slug,
because the site already links to that address. An impressum the developer declared is made a
notice before its first version is published, so nobody is ever asked to agree to it.

**Why this priority**: A declaration is only worth something if the address it names cannot be
moved out from under the links. It is P2 because the declared documents are useful from US-1 alone.

**Independent Test**: In the admin, open a declared document that has no version. Confirm the slug
cannot be changed and the name, kind and enforcement can. Try to change the slug from code and
confirm it is refused. Remove the declaration and confirm the slug can be changed again while the
document still has no published version.

**Acceptance Scenarios**:

1. **Given** a declared document with no version, **When** it is opened in the admin, **Then** its
   slug is shown and cannot be changed, and its name, kind and enforcement can.
2. **Given** a declared document with no version, **When** code changes its slug, by saving it or
   by updating it in bulk, **Then** the change is refused and the slug stays as declared.
3. **Given** a declared document, **When** its kind is changed to a notice before its first version
   is published, **Then** publishing a version never makes it outstanding for anybody.
4. **Given** a document whose declaration has been removed and which has no published version,
   **When** its slug is changed, **Then** the change is allowed, as for any undeclared document.

---

### Edge Cases

- A declared document deleted in the admin before it has a version is created again the next time
  the database is migrated, because the declaration still names it.
- A slug cannot be declared twice, because each declaration is keyed by its slug.
- A declared slug changed in the settings is a new declaration. A document is created under the new
  slug, as long as its name collides with no other document (US-1, scenario 9). The document under
  the old slug stays as it was, no longer declared.
- A declaration whose name is the declared document's own is never a conflict with itself.
- A project that keeps the package's tables on a database other than the default gets the declared
  documents wherever the package's documents are kept.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A developer MUST be able to declare, in the project's settings, the documents the site
  links to, each by a slug and a name. *(US-1)*
- **FR-002**: When the database is migrated, every declared document whose slug no document has
  MUST be created with the declared slug and name and no version. *(US-1)*
- **FR-003**: A document created from a declaration MUST start with the same kind and enforcement as
  a document created in the admin with nothing chosen. *(US-1)*
- **FR-004**: Migrating MUST NOT change a document that already exists, declared or not: not its
  name, kind, enforcement, versions or acceptances. *(US-1)*
- **FR-005**: A document created in the admin whose slug is later declared MUST become the declared
  document, unchanged. *(US-1)*
- **FR-006**: Removing a declaration MUST NOT delete or change the document it named. *(US-1)*
- **FR-007**: A declared document with no version MUST behave as any document with no version does:
  no page, not listed beside other documents' pages, never outstanding, never stopping anybody.
  *(US-1)*
- **FR-008**: When a declaration's name already belongs to another document, or its slug is not one
  a document may have, migrating MUST tell the project which declaration is at fault and with what,
  and MUST create no declared document in that run. *(US-1)*
- **FR-009**: A project that declares nothing MUST see no document created or changed by migrating.
  *(US-1)*
- **FR-010**: Declared documents MUST exist in the test database a project's test run sets up.
  *(US-1)*
- **FR-011**: A declared document's slug MUST NOT be changeable while it is declared, whether or not
  a version has been published, from the admin or from code, including in bulk. *(US-2)*
- **FR-012**: A declared document's name, kind and enforcement MUST stay changeable as any
  document's are. *(US-2)*
- **FR-013**: A document that is no longer declared MUST follow the slug rule every undeclared
  document follows: changeable until its first version is published, fixed after. *(US-2)*
- **FR-014**: Every user-facing string this feature adds MUST be translatable. *(US-1, US-2)*
- **FR-015**: The documentation MUST explain how to declare documents, when they are created, that
  the name is a starting value and the slug is fixed, that kind and enforcement are set in the
  admin, what a link to a declared document shows before its first version is published, and what
  happens when a declaration is changed or removed. *(US-1, US-2)*
- **FR-016**: The glossary MUST define a declared document, and its entry for *Slug* MUST say when a
  declared document's slug is fixed. *(US-1, US-2)*

### Key Entities

- **Document** (FS-001, FS-007, FS-010): unchanged in shape. A document is declared when the
  project's settings name its slug. Being declared fixes its slug and nothing else.
- **Version** (FS-001, FS-002): unchanged. A declaration never creates one.
- **Acceptance** (FS-003): unchanged. This feature never creates or changes one.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer links to a document from a template, and once a version is published the
  link reaches that document in every environment, with no step beyond declaring it and migrating.
- **SC-002**: After migrating, a new database holds every declared document. An existing database
  holds exactly the documents, versions and acceptances it held before, plus any declared document
  that was missing.
- **SC-003**: Migrating any number of times in a row creates each declared document once and
  changes nothing after the first run.
- **SC-004**: No route the package offers, in the admin or in code, moves a declared document's
  slug.
- **SC-005**: A project that declares nothing has the same database contents before and after
  migrating.

## Clarifications

### Session 2026-10-20

- **Q**: Does a declaration set whether a document is agreed to or a notice, or whether it is
  enforced? → **A**: No (Scope, FR-003, FR-012). Both are for whoever manages the documents to
  decide, and the maintainer ruled that a developer should not dictate them. A declared impressum
  starts as a document people agree to, exactly as one created in the admin does today, and its
  editor makes it a notice before publishing it (US-2, scenario 3).
- **Q**: When are declared documents created: the first time something reads them, or when the
  database is migrated? → **A**: When the database is migrated (FR-002). Creating them on first read
  would write to the database while a page is being drawn, and the documents an editor sees would
  depend on which pages had been visited. Every environment, test databases included, is migrated
  already.
- **Q**: Is a declared document's slug fixed before its first version is published? → **A**: Yes
  (FR-011). ADR 0019 fixes a slug at first publication because that is when the first link to it
  can exist. A declaration is the developer saying that a link exists already.
- **Q**: What happens when a declared name already belongs to another document? → **A**: Migrating
  says so and creates no declared document (FR-008). Quietly skipping that one declaration would
  leave the code linking to a document that will never exist, which is the failure this feature
  removes.
- **Q**: Does changing a declared name rename the document? → **A**: No (FR-004, scenario 6). Once
  the document exists its name belongs to whoever manages the documents, so a later edit to the
  settings cannot undo a rename made in the admin.

## Assumptions

- FS-001 to FS-010 are delivered, and this spec is written against them as they stand on main. A
  document with no version is already handled everywhere the package reads documents.
- A declared document starts as a document people agree to, enforced, as ADR 0023 has every new
  document start.
- Besides the slug, the name is the one thing a declaration has to carry, because a document cannot
  exist without one and names are unique.
- A declaration holds no personal data, so Article XIV does not apply.
- No new screen is added. The admin's document form shows a declared document's slug read-only, as
  it already does for a published document. The feature is built without a design prototype.
