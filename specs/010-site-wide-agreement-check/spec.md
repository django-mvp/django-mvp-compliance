# Feature Specification: Applying the agreement check across the whole site

**Feature Branch**: `010-site-wide-agreement-check`

**Created**: 2026-10-12

**Status**: Draft

**Serves**: G3 · **Roadmap**: R5 · **Issue**: #87

**Input**: Once there is a page that asks a person to agree, a project needs a way to make sure
everybody with something outstanding reaches it. Marking up views one at a time is not dependable,
because the view somebody forgets is exactly where a person who has not agreed ends up. A developer
should be able to switch the check on for the whole site in one place. From then on a signed-in
person with something outstanding is sent to the page that asks them, whatever they were trying to
open. Some addresses have to stay reachable or a person is caught in a loop, some accounts need to
be let past, and not every document people agree to is worth stopping them over. None of it should
make every page slower for the people with nothing outstanding, who are nearly everybody.

## Scope

Issue #86 builds the page that asks a person to agree, records the acceptance and returns them to
where they were going. This feature decides when a person is sent there.

A developer switches the check on by adding one middleware to the project's settings. Nothing is
checked until they do, so installing or upgrading the package changes nothing on its own. With the
check on, a signed-in user who has not accepted the current version of an enforced document is sent
to the page that asks, whatever address they asked for. The address they wanted goes with them, so
the page can return them to it.

Four things shape who is stopped and where:

- Enforcement is set on each document by whoever manages the documents. Only an enforced document
  stops anybody. A document people agree to that is not enforced stays outstanding for the people
  who have not accepted it, and they can accept it whenever they choose.
- Some addresses stay reachable without any configuration: the page that asks, the documents'
  own pages, signing out, and the site's static and media files. A project adds its own.
- Some accounts are let past, either listed by name in the project's settings or because they hold
  a permission the package provides.
- A user found to have nothing stopping them is not checked against the database again on every
  request. A change that could stop them reaches them within a delay the project sets.

Some things stay out of this feature:

- The page that asks, what it shows, recording the acceptance and returning the person are
  issue #86. This feature only sends people there.
- Whether a document is one people agree to or a notice is already delivered (FS-007, issue #65).
  A notice is never outstanding, so it never stops anybody whatever its enforcement says.
- What a person still has outstanding is already answered (FS-003) and that answer does not
  change. It still covers every document people agree to, enforced or not.
- Visitors who are not signed in are never checked. An acceptance names a user, so there is nobody
  to ask. Requiring a sign-in is the project's own business.
- Telling a person what changed between versions is roadmap item R6.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Switching the check on for the whole site (Priority: P1)

A developer adds the package's middleware to the project's settings and marks up no views. From
then on, a signed-in user who has not accepted the current version of an enforced document is sent
to the page that asks, from any address on the site, and returns to the address they wanted once
they have agreed. A user with nothing enforced outstanding notices nothing. The user who is stopped
can still read the documents and sign out, and the page they are sent to still loads its styles,
with no extra configuration.

**Why this priority**: It is the feature. Without it a project has to protect views one at a time,
and the view somebody forgets is where a person who has not agreed gets through.

**Independent Test**: In the demo, add the middleware, publish a version of an enforced document
and sign in as a user who has not accepted it. Open several unrelated addresses and confirm each
one leads to the page that asks, carrying the address that was requested. Confirm the document's
own page and signing out still open. Record the user's acceptance and confirm every address opens
normally afterwards.

**Acceptance Scenarios**:

1. **Given** the check is switched on and a signed-in user has not accepted the current version of
   an enforced document, **When** they request any address that is not kept reachable, **Then** they
   are redirected to the page that asks, and the address they requested is passed to it.
2. **Given** the same user, **When** their acceptance of that version is recorded, **Then** their
   very next request for the address they wanted is served normally.
3. **Given** the check is switched on and a signed-in user has accepted the current version of
   every enforced document, **When** they request any address, **Then** it is served normally.
4. **Given** the check is switched on, **When** a visitor who is not signed in requests any
   address, **Then** it is served exactly as it would be without the check.
5. **Given** a user who is being stopped, **When** they request the page that asks, the page of any
   document, or the address that signs them out, **Then** each is served and none redirects.
6. **Given** a user who is being stopped, **When** their browser requests a static or media file,
   **Then** the file is served.
7. **Given** a user who is being stopped, **When** they submit a form to an address that is not
   kept reachable, **Then** the submission does not reach its view, they are redirected to the page
   that asks, and no return address is passed for a request that cannot be repeated by visiting it.
8. **Given** a user who is being stopped, **When** a request made from inside a page, for part of a
   page, is refused, **Then** the user ends up on the page that asks as a whole page, not with that
   page placed inside the one they were on.
9. **Given** a project that has not added the middleware, **When** any user with something
   outstanding requests any address, **Then** nobody is redirected.
10. **Given** a signed-in user already found to have nothing stopping them, **When** they request
    further pages, **Then** the check adds no database query to those requests.
11. **Given** a user who has two enforced documents outstanding, **When** they request any address,
    **Then** they are redirected once, to the one page that asks.
12. **Given** the middleware is added but the page that asks cannot be reached, because the
    package's addresses are not mounted or the middleware sits ahead of the one that identifies the
    signed-in user, **When** the project's checks are run, **Then** the developer is told what is
    wrong, and no request is redirected to an address that does not exist.

---

### User Story 2 - Deciding which documents stop a person (Priority: P1)

A compliance editor publishes terms of use that everybody must accept, and a cookie policy that
people may accept in their own time. In the admin they mark the terms as enforced and leave the
cookie policy not enforced. Users who have not accepted the terms are stopped. Nobody is stopped
over the cookie policy, although it still counts among what a person has outstanding and can be
accepted at any time. The setting can be changed later in either direction without touching any
acceptance.

**Why this priority**: The site-wide check is only usable if it stops people over the right
documents. Without a say per document, switching the check on would stop every user over every
document, and a project with a cookie policy could not switch it on at all.

**Independent Test**: In the demo with the check on, publish two documents people agree to, one
enforced and one not. Sign in as a user who has accepted neither. Confirm they are stopped, record
their acceptance of the enforced document only, and confirm they now browse freely while the other
document is still among what they have outstanding.

**Acceptance Scenarios**:

1. **Given** a document people agree to that is not enforced, with a version in force, **When** a
   signed-in user who has not accepted it requests any address, **Then** they are not redirected.
2. **Given** that same document and user, **When** what the user still has outstanding is worked
   out, **Then** the document is among it.
3. **Given** an enforced document and one that is not, both outstanding for a user, **When** the
   user's acceptance of the enforced one is recorded, **Then** the user is no longer redirected.
4. **Given** a new document being created in the admin, **When** nobody chooses, **Then** it is
   enforced.
5. **Given** the admin's list of documents, **When** it is read, **Then** it shows whether each
   document is enforced.
6. **Given** an enforced document with recorded acceptances, **When** its enforcement is switched
   off, through the admin or from code, **Then** no version and no acceptance changes, and users who
   have not accepted it stop being redirected once the change has reached them.
7. **Given** a document that is not enforced, **When** its enforcement is switched on, **Then**
   users who have not accepted its current version are redirected once the change has reached them.
8. **Given** a notice marked as enforced, **When** any user requests any address, **Then** nobody
   is redirected because of it.
9. **Given** an enforced document that has only drafts, **When** any user requests any address,
   **Then** nobody is redirected because of it.
10. **Given** a user and code in the project, **When** the code asks which enforced documents the
    user has outstanding, **Then** it gets exactly the documents the check would stop that user
    over, at a number of database queries that does not grow with the number of documents.

---

### User Story 3 - Keeping a project's own addresses reachable (Priority: P2)

A developer's site has addresses that must work for a user who has not agreed yet: a health check
that a signed-in monitoring account calls, a payment provider's callback, a help page. They list
those addresses in the project's settings, and the check leaves them alone. The addresses that
work by default keep working alongside the ones the project added.

**Why this priority**: The defaults keep a person out of a loop, which is enough for the check to
be usable. This covers the addresses only the project knows about.

**Independent Test**: In the demo with the check on and a user who is being stopped, add an address
to the project's list and confirm it and everything beneath it are served to that user, while an
address not on the list still redirects.

**Acceptance Scenarios**:

1. **Given** a project that has listed an address to keep reachable, **When** a user who is being
   stopped requests that address or one beneath it, **Then** it is served.
2. **Given** the same project, **When** that user requests an address that is not listed and not
   reachable by default, **Then** they are redirected.
3. **Given** a project that has listed addresses of its own, **When** a user who is being stopped
   requests the page that asks, a document's page or the address that signs them out, **Then**
   each is still served.
4. **Given** a listed address, **When** a user who is being stopped requests a different address
   that merely begins with the same characters but is not beneath it, **Then** they are redirected.

---

### User Story 4 - Letting particular accounts past (Priority: P2)

A developer has accounts that should never be stopped: the account a monitoring service signs in
with, the accounts a browser test suite drives, the support team. They name the first two in the
project's settings. For the support team, an administrator gives its group a permission the package
provides, with no deploy. Those accounts open every address whatever they have outstanding. Being
let past records nothing: what those accounts have outstanding is unchanged, and they can still
accept a document themselves.

**Why this priority**: A site can run the check without this, by having those accounts accept the
documents. It matters as soon as an automated account meets a newly published version in the
middle of the night.

**Independent Test**: In the demo with the check on and an enforced document outstanding for three
users, name one in the settings, give another the permission, and leave the third alone. Confirm
the first two open any address and the third is redirected, and that no acceptance was created for
anybody.

**Acceptance Scenarios**:

1. **Given** an account named in the project's settings, with an enforced document outstanding,
   **When** it requests any address, **Then** it is served.
2. **Given** an account that holds the package's permission, directly or through a group, with an
   enforced document outstanding, **When** it requests any address, **Then** it is served.
3. **Given** an account that is let past, **When** it requests any address, **Then** no acceptance
   is created and what it has outstanding is unchanged.
4. **Given** an account that is neither named nor holds the permission, **When** it requests an
   address with an enforced document outstanding, **Then** it is redirected.
5. **Given** an account that was let past by the permission, **When** the permission is taken away,
   **Then** it is redirected on its next request with an enforced document outstanding.
6. **Given** signed-in users with nothing enforced outstanding and no accounts named, **When** they
   request pages, **Then** deciding whether to let them past adds no database query.

---

### User Story 5 - Choosing how soon a change reaches people (Priority: P3)

A developer running a busy site accepts that a newly published version starts stopping people a
short while after it is published and not on the same instant, in exchange for the check costing
nothing on ordinary requests. The delay has a default and the developer can shorten it, lengthen
it, or set it to nothing so that every request is checked against the database.

**Why this priority**: The default is workable for most sites. This is for the site that needs a
publication to bite at once, or one that would trade a longer delay for fewer checks.

**Independent Test**: In the demo with the check on, let a user browse with nothing outstanding,
then publish a new version of an enforced document. Confirm the user is redirected no later than
the configured delay after publication, and on their very next request when the delay is set to
nothing.

**Acceptance Scenarios**:

1. **Given** a user found to have nothing stopping them, **When** a new version of an enforced
   document is published, **Then** the user is redirected on a request made no later than the
   configured delay after publication.
2. **Given** a project that has set the delay to nothing, **When** a new version of an enforced
   document is published, **Then** every user who has not accepted it is redirected on their very
   next request.
3. **Given** a project that has set no delay of its own, **When** the check runs, **Then** the
   default delay applies and is no longer than one minute.
4. **Given** a user who is being stopped, **When** their acceptance is recorded, **Then** they are
   let through on their next request whatever the delay is set to.
5. **Given** a user whose acceptance could not be recorded, **When** they request any address,
   **Then** they are still redirected whatever the delay is set to.

---

### Edge Cases

- A user is stopped and will not agree. They can read the documents and sign out, and reach
  nothing else unless the project has kept it reachable.
- A new version of an enforced document is published while a user is in the middle of a session.
  They are stopped on a later request, within the configured delay, and not in the middle of the
  request that was already being served.
- A compliance editor publishes a new version of an enforced document and is then stopped
  themselves in the admin, like any other user, unless the project keeps the admin reachable or the
  editor is let past.
- A superuser holds every permission, so a superuser is let past. The documentation says so.
- The address a stopped user asked for is one that is kept reachable. Nothing is passed to the
  page that asks, because they are never sent there for it.
- A document's kind is changed from a notice to a document people agree to while it is enforced.
  It starts stopping the people who have not accepted its current version, within the configured
  delay.
- An enforced document's current version is superseded by a new one. A user who accepted the old
  version is stopped again, because enforcement is measured against the current version.
- Two requests from the same stopped user arrive together. Both are redirected, and neither
  records anything.
- The project signs people out at an address the package cannot work out for itself. The project
  lists it, and the documentation says when that is needed.
- A user's account is named in the settings and is also deleted. The name matches nobody and
  nothing fails.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A developer MUST be able to switch the check on for the whole site by adding one
  middleware to the project's settings, with no change to any view. *(US-1)*
- **FR-002**: Without that middleware the package MUST NOT redirect anybody, so installing or
  upgrading it changes no request. *(US-1)*
- **FR-003**: With the check on, a signed-in user who has not accepted the current version of at
  least one enforced document MUST be redirected to the page that asks (issue #86) from every
  address that is not kept reachable, by every request method. *(US-1)*
- **FR-004**: The redirect MUST pass the requested address to that page in the way issue #86
  defines for returning a person, when the request is one that can be repeated by visiting the
  address. For any other request it MUST pass none. *(US-1)*
- **FR-005**: A visitor who is not signed in MUST never be redirected by the check. *(US-1)*
- **FR-006**: The following MUST stay reachable for a user who is being stopped, with no
  configuration: the page that asks, every address the package itself serves, the address that
  signs a person out, and the site's static and media files. *(US-1)*
- **FR-007**: A request for part of a page that is refused by the check MUST lead the user to the
  page that asks as a whole page. *(US-1)*
- **FR-008**: A user with several enforced documents outstanding MUST be redirected once, to the
  one page that asks. *(US-1)*
- **FR-009**: When the middleware is present and the page that asks cannot be resolved, or the
  signed-in user is not known at the point the check runs, the project's checks MUST report it,
  naming what to change. *(US-1)*
- **FR-010**: Each document MUST carry whether it is enforced. A document for which nobody chose
  MUST be enforced. *(US-2)*
- **FR-011**: Only an enforced document people agree to, with a version in force that the user has
  not accepted, MUST stop a user. A notice, a document that is not enforced and a document with no
  version in force MUST never stop anybody. *(US-2)*
- **FR-012**: Enforcement MUST NOT change what a user has outstanding: a document that is not
  enforced still counts towards it, and its acceptance can still be recorded. *(US-2)*
- **FR-013**: Enforcement MUST be changeable at any time, from the admin and from code, and
  changing it MUST NOT change any version or any acceptance. *(US-2)*
- **FR-014**: The admin MUST let enforcement be chosen when a document is created and changed
  afterwards, and its list of documents MUST show it for each document. *(US-2)*
- **FR-015**: The package MUST answer, from code, which enforced documents a user has outstanding,
  as the same answer the check acts on, at a number of database queries that does not grow with
  the number of documents. *(US-2)*
- **FR-016**: A project MUST be able to list, in its settings, addresses to keep reachable. A
  listed address MUST cover itself and everything beneath it, and nothing else. *(US-3)*
- **FR-017**: Addresses a project lists MUST add to the ones reachable by default and MUST NOT
  replace them. *(US-3)*
- **FR-018**: A project MUST be able to name accounts in its settings that are never redirected.
  *(US-4)*
- **FR-019**: The package MUST provide a permission whose holders, directly or through a group,
  are never redirected. *(US-4)*
- **FR-020**: Letting an account past MUST NOT record an acceptance or change what that account
  has outstanding. *(US-4)*
- **FR-021**: For a signed-in user already found to have nothing stopping them, the check MUST add
  no database query to a request until the configured delay has passed. That covers deciding
  whether the account is let past. *(US-1, US-4, US-5)*
- **FR-022**: A change that could stop a user (a version published, a document's enforcement or
  kind changed) MUST reach every signed-in user within a delay the project can set. The default
  MUST be no longer than one minute, and a project MUST be able to set it to nothing. *(US-5)*
- **FR-023**: Only the finding that nothing stops a user may be remembered between requests. A
  user who is being stopped MUST be checked afresh on each request, so a recorded acceptance lets
  them through at once and a failed one never does. *(US-1, US-5)*
- **FR-024**: Upgrading an existing installation MUST leave every existing document enforced and
  MUST NOT drop or change any version or acceptance. *(US-2)*
- **FR-025**: Every user-facing string this feature adds MUST be translatable. *(US-2, US-4)*
- **FR-026**: The documentation MUST explain how to switch the check on and where the middleware
  goes, which addresses stay reachable by default and how to add more, how to let accounts past
  and that a superuser always is, how enforcement is set per document, and what the delay means
  for a newly published version. *(US-1, US-2, US-3, US-4, US-5)*
- **FR-027**: The glossary's entry for *Enforcement* MUST say that it is set on the document, that
  a new document is enforced, and that it only takes effect on a site that has switched the check
  on. *(US-2)*

### Key Entities

- **Document** (FS-001, FS-007): gains whether it is enforced. Like its kind, this is not frozen by
  publication.
- **Version** (FS-001, FS-002): unchanged. Enforcement is measured against the current version.
- **Acceptance** (FS-003): unchanged. This feature reads acceptances and never creates, edits or
  removes one.
- **User**: unchanged. Being let past is decided from the account's name or its permissions, and
  nothing about it is stored on the account by this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer switches the check on for a whole site by changing one setting, with no
  view marked up.
- **SC-002**: With the check on, a signed-in user with an enforced document outstanding reaches no
  address outside the reachable ones without first being sent to the page that asks.
- **SC-003**: A user who is being stopped can always reach the page that asks, read every
  document and sign out, on a project that has configured nothing.
- **SC-004**: A signed-in user with nothing enforced outstanding can open one hundred pages in a
  row with the check adding a database query to at most one of them per configured delay.
- **SC-005**: After a new version of an enforced document is published, every signed-in user who
  has not accepted it is stopped within the configured delay, which is one minute or less unless
  the project chose otherwise.
- **SC-006**: Switching enforcement off for a document, and on again, leaves the count and content
  of versions and acceptances unchanged.
- **SC-007**: An account named in the settings or holding the permission is never redirected, and
  no acceptance exists for it that it did not give itself.
- **SC-008**: After upgrading, a project that has not added the middleware serves every request
  exactly as it did before.

## Clarifications

### Session 2026-10-12

- **Q**: Is a new document enforced or not when nobody chooses? → **A**: Enforced (FR-010). The
  check itself is off until a developer adds the middleware, so this default stops nobody on its
  own. A developer who switches the check on expects it to do something, and a default of not
  enforced would leave the site looking protected while stopping nobody. The compliance editor
  switches it off for the documents that should not stop people, such as a cookie policy.
- **Q**: Does switching enforcement off remove a document from what a person has outstanding? →
  **A**: No (FR-012). Outstanding stays the answer for every document people agree to, as ADR 0009
  already decided. The check narrows it to enforced documents, and that narrower answer is
  available from code (FR-015).
- **Q**: What happens to a form submission, or to a request for part of a page, from a user who is
  being stopped? → **A**: Both are stopped. A submission is redirected without a return address,
  because visiting the address again would not repeat it (FR-004). A request for part of a page
  takes the user to the page that asks as a whole page (FR-007). Letting either through would be
  the forgotten view this feature exists to close.
- **Q**: How soon after a version is published must people be stopped? → **A**: Within a delay the
  project sets, one minute or less by default, with nothing as a permitted value (FR-022). Checking
  the database on every request is the cost the issue rules out, and stopping people at the exact
  instant of publication would need shared infrastructure the package cannot assume a project has.
  Only the finding that nothing stops a user is remembered (FR-023), so the delay never sends
  somebody who has just agreed back to the page, and never lets through somebody whose acceptance
  failed.
- **Q**: Is the permission that lets accounts past one the package provides, or one the project
  names? → **A**: One the package provides (FR-019). An administrator grants it to a group in the
  admin with no deploy, and there is no setting to get wrong. It is checked the way Django checks
  any permission, so a superuser holds it.

## Assumptions

- FS-001 to FS-008 are delivered, and this spec is written against them as they stand on main: what
  a user has outstanding is worked out in one query, a document is either one people agree to or a
  notice, and each document has a page among the addresses the package serves.
- Issue #86 delivers the page that asks, at an address among the ones the package serves, and a
  documented way to send a person to it with the address they should return to. This feature uses
  that way and adds no second one. It is built after #86.
- What the page that asks shows, including whether it also offers documents that are outstanding
  but not enforced, is for issue #86 to decide. This feature only needs the user to be let through
  once every enforced document is accepted.
- The project uses Django's sessions and authentication middleware, as django-mvp already
  requires.
- Whether a document is enforced is not personal data, and the names of accounts let past live in
  the project's own settings, so Article XIV does not apply.
- No new screen is added. The only change a person sees in the package's own pages is one more
  field on the admin's document form and one more column in its list of documents, so the feature
  is built without a design prototype.
