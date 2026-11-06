# Feature Specification: Translations of a published version

**Feature Branch**: `015-translations-of-a-version`

**Created**: 2026-11-06

**Status**: Draft

**Serves**: G4 · **Roadmap**: R7 · **Issue**: #155

**Input**: A site whose readers don't all speak one language needs its legal documents in more than
one. A compliance editor should be able to add a translation of a published version, and correct it
later, without touching the version itself. The version stays the text its acceptances point at,
and the one that governs in a dispute. Translations arrive on their own schedule, often weeks after
the version is published. They get corrected when a translator finds a mistake. None of that should
ever disturb what people have already agreed to, or need a new version to be published.

## Scope

A compliance editor writes a translation of a version into one of the languages the site offers,
previews it, and puts it live, all from the admin, without a deploy and without a new version. A
translation covers the version's wording and its summary.

A version can be translated once its wording is settled, and not before. To translate a version
before it goes into force, an editor first **locks it for translation**: the version becomes
**pending**, its wording and summary can no longer change, and translators work against text that
will not move under them. A translation put live on a pending version goes live when the version is
published, so a site can launch a version and its translations on the same day. A published version
can be translated too, weeks later if need be. Locking is optional: a site that does not translate
publishes straight from a draft, exactly as before.

A pending version has no number and no legal standing. Nobody is asked to agree to it, and only the
people who manage documents can see it. If a mistake turns up while it is being translated, it can
be returned to draft, and its translations return to draft with it, so they are checked again
against the corrected wording. A pending version can also be discarded, like a draft.

A live translation can be corrected. A correction replaces the wording readers will be served from
then on. The wording it replaces is kept, with the dates it was live, because a person may have
read it when they agreed and what they saw must still be producible later (G2).

The version itself never changes. Its own text is in the site's main language, it is still what
every acceptance points at, and it is the text that governs. A translation is an aid to reading it.

Translating is a permission of its own, separate from publishing versions, because the translator
is often not the person who decides the wording. The admin shows, for each pending or published
version, which of the site's languages it has a live translation in and which it lacks.

A developer can add and correct translations from code, the way a version can already be published
from code, and the package sends a signal whenever a version or a translation changes state. A
project can then, for instance, have a version that reaches pending translated automatically.

Some things stay out of this feature:

- What a reader is served, on a document's page and on the page asking them to agree, is issue
  #156. Until it lands, nothing a reader sees changes: a live translation is held and listed in the
  admin and shown nowhere else.
- Whether an acceptance records which translation was on screen is issue #156.
- Comparing two translations, or a translation with its version, is not part of R7.
- The email announcing a new version (FS-005), the copy a person downloads (FS-012) and the page
  staff use to produce everything held about a person (FS-004) are unchanged.
- The package ships no list of languages and no machine translation. A translation written by a
  project's own code is the project's.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Translating a version, and correcting the translation later (Priority: P1)

The privacy policy's next version is written and agreed internally. The site also offers German.
An editor locks it for translation. A translator who can translate documents but not publish
versions opens it in the admin, sees that it has no German translation yet, and writes one,
including its summary. They preview it, the way a version is previewed, and put it live. When the
version is published the next week, the German translation goes live with it. The version is
exactly as it was locked, and so is every acceptance of it.

Three weeks later a reader points out a mistranslated clause. The translator corrects it and puts
the correction live. From then on the corrected wording is the German translation. The wording it
replaced is still on record, with the dates it was live.

**Why this priority**: It is the feature. Without it no translation exists, and #156 has nothing to
show.

**Independent Test**: With German among the site's languages, lock a draft for translation, then as
an account holding only the permission to translate, write a German translation, preview it and put
it live. Check it is not live until the version is published, and is once it is. Check the version's
wording, summary, number and stored HTML are unchanged, and its acceptances untouched. Correct the
translation and put the correction live. Check the corrected wording is the live one, and the
earlier wording is still held with the dates it was live.

**Acceptance Scenarios**:

1. **Given** a draft, **When** someone with the permission to publish locks it for translation,
   **Then** it becomes pending, and its wording and summary can no longer be changed by any route
   the package offers.
2. **Given** a pending version, **When** it is looked at by anyone without access to the admin's
   documents, or asked about as what is in force, outstanding or comparable, **Then** it is treated
   exactly as a draft is: invisible, unnumbered and without standing.
3. **Given** a pending version, **When** it is published, **Then** it is published exactly as a
   draft would be, and any translation put live on it goes live at the same moment.
4. **Given** a pending version, **When** it is returned to draft, **Then** it is editable again,
   and every translation of it that was put live returns to draft, keeping its wording.
5. **Given** a pending version, **When** it is discarded, **Then** it and its translations are
   removed, as a draft is.
6. **Given** a draft, **When** a translation of it is attempted, **Then** it is refused.
7. **Given** a pending or published version and a language the site offers other than its main
   one, **When** someone with the permission to translate writes a translation of the version in
   that language, **Then** it is held as not yet live, and nobody without access to the admin's
   documents can see it.
8. **Given** a translation that is not yet live, **When** it is previewed, **Then** it is shown as
   it will be served, from the same rendering a version goes through at publication.
9. **Given** a translation that is not yet live, **When** it is put live, **Then** its wording is
   rendered and stored at that moment, and the stored wording is what is served from then on.
10. **Given** a version with live translations, **When** it is read, **Then** its wording, summary,
    number, stored HTML, publication date and publisher are exactly as before any translation
    existed, and no acceptance of it has changed.
11. **Given** a live translation, **When** it is corrected and the correction is put live, **Then**
    the corrected wording is the live translation from that moment, and the wording it replaced is
    kept unchanged, with the times it went live and was replaced.
12. **Given** a live translation, **When** anybody tries to change its stored wording by any route
    the package offers, other than putting a correction live, **Then** the change is refused.
13. **Given** a version, **When** a translation is written for it, **Then** the translation can hold
    a translated summary as well as the translated wording, and a version with no summary has none
    to translate.
14. **Given** a language that the site does not offer, or the site's main language, **When** a
    translation in it is attempted, **Then** it is refused.
15. **Given** a version that already has a translation in a language, **When** a wording in that
    language is added, **Then** it is a correction of that translation, never a second translation.
16. **Given** an account with the permission to translate and not the permission to publish
    versions, **When** it uses the admin, **Then** it can write, preview, put live and correct
    translations, and cannot lock, return, publish, edit or discard a version.
17. **Given** an account without the permission to translate, **When** it tries to put a
    translation or a correction live, **Then** it is refused.
18. **Given** a pending or published version, **When** it is viewed in the admin, **Then** it shows
    which of the site's languages it has a live translation in and which it has none in, and the
    list of versions can be narrowed to those missing a translation.
19. **Given** a notice, **When** its version is translated, **Then** it is translated exactly as a
    document people agree to.
20. **Given** a translation put live or corrected, **When** it is looked at later, **Then** it
    names the account that put it live, kept as the publisher of a version is kept, including after
    that account is removed.

---

### User Story 2 - A developer automates translations from code (Priority: P3)

A site keeps its translated documents in its repository and loads them on deploy. Another sends new
versions to a translation service. Their developer connects to the signal the package sends when a
version becomes pending, and from code adds the translations, puts them live, and later puts
corrections live, with the same results as doing it in the admin. Other signals tell the project
when a version is returned to draft, when it is published, and when a translation goes live or
returns to draft.

**Why this priority**: The admin covers every site. This saves a site that already manages its
translations elsewhere from retyping them, and it matches publishing a version from code, which the
package already offers.

**Independent Test**: Connect a receiver to the pending signal that adds and puts live a German
translation from code. Lock a draft for translation and check the translation exists and goes live
when the version is published. Put a correction live from code. Check every change of state sent
its signal once, after it committed, and that a translation in a language the site does not offer
raises.

**Acceptance Scenarios**:

1. **Given** a pending or published version, **When** a developer adds a translation in an offered
   language from code and puts it live, **Then** the result is the same as doing it in the admin,
   with nobody named as having put it live unless the call names an account.
2. **Given** a live translation, **When** a developer puts a correction live from code, **Then**
   the earlier wording is kept exactly as when it is corrected in the admin.
3. **Given** a call that the admin would refuse, such as a language the site does not offer or a
   draft version, **When** it is made from code, **Then** it raises the package's own exception,
   and nothing is written.
4. **Given** a version or a translation that changes state, by any route the package offers,
   **When** the change commits, **Then** the package sends one signal naming the change, the object
   and the account that made it, and a receiver that raises cannot undo the change.
5. **Given** a change of state that is refused or rolled back, **When** it ends, **Then** no signal
   is sent.
6. **Given** a developer reading the documentation, **When** they look for how to translate a
   version, **Then** it explains what a translation is, what governs, locking a version for
   translation, adding and correcting a translation in the admin and from code, every signal and
   when it is sent, and the permissions involved.

---

### Edge Cases

- A language is removed from the site's `LANGUAGES` after translations into it were put live. They
  are kept, never deleted, and the admin shows them as in a language the site no longer offers.
- The site's main language is changed after translations exist. Nothing is rewritten. A translation
  that now shares the main language is kept and flagged in the admin.
- A version is superseded. Its translations stay, and can still be corrected, because a person
  holding an acceptance of it may still read it.
- A new version is published the day after a translation of the old one went live. The new version
  starts with no translations. Nothing is carried over from the one it replaces.
- Two people correct the same translation at once. Both corrections are kept, the later one put
  live is the live translation, and neither is lost.
- A translated wording contains markup the sanitiser does not allow. It is removed exactly as for a
  version.
- A site offers only one language, or has not set `LANGUAGES` at all. Nothing about translations
  appears in the admin. Locking for translation is still offered, and a pending version publishes
  as a draft would.
- A document has a pending version and a draft at once. Either can be published. Publishing the
  draft leaves the pending version pending, to be published after it or discarded.
- A receiver of a signal raises. The change it was told about stands, and the other receivers still
  run.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A compliance editor MUST be able to write a translation of a pending or published
  version into any language in the site's `LANGUAGES` other than its main language
  (`LANGUAGE_CODE`), from the admin, without a deploy or a migration. No language is offered while
  the site has not set `LANGUAGES` itself. *(US-1)*
- **FR-002**: A translation MUST hold the translated wording of a version and MAY hold a translated
  summary. *(US-1)*
- **FR-003**: A version MUST have at most one translation per language. A wording added in a
  language that already has a translation is a correction of it. *(US-1, US-2)*
- **FR-004**: A translation MUST be previewable before it is live, through the same rendering a
  version goes through. *(US-1)*
- **FR-005**: Putting a translation live MUST render and store its HTML at that moment, and the
  stored HTML MUST be what is served afterwards. Markdown MUST NOT be rendered at request time.
  *(US-1)*
- **FR-006**: A translation put live on a pending version MUST NOT be live until the version is
  published. Discarding a pending version MUST discard its translations. *(US-1)*
- **FR-007**: Writing, putting live or correcting a translation MUST NOT change any field of its
  version, or any acceptance. *(US-1, US-2)*
- **FR-008**: Once a wording of a translation has been live, it MUST never be changed or deleted by
  any route the package offers. A correction MUST be a new wording that replaces it, and the
  wording it replaces MUST be kept with the times it went live and was replaced. *(US-1, US-2)*
- **FR-009**: Each live wording of a translation MUST record the account that put it live, kept as a
  version's publisher is kept, or record that nobody was named. *(US-1, US-2)*
- **FR-010**: Translating MUST be a permission of its own, separate from publishing a version, and
  putting a translation or a correction live MUST require it. The permission MUST NOT allow
  locking, returning, publishing, editing or discarding a version. *(US-1)*
- **FR-011**: The admin MUST show, for each pending or published version, which offered languages
  it has a live translation in and which it has none in, and MUST let the list of versions be
  narrowed to those missing a translation. *(US-1)*
- **FR-012**: Translations MUST work the same for notices as for documents people agree to.
  *(US-1)*
- **FR-013**: A translation MUST never be presented as the text that governs or as the text an
  acceptance points at. *(US-1)*
- **FR-014**: A developer MUST be able to add a translation, put it live and put a correction live
  from code, with the same rules and results as the admin, and a refused call MUST raise the
  package's own exception and write nothing. *(US-2)*
- **FR-015**: Translations in a language the site no longer offers, or in the site's main language
  after it changes, MUST be kept and MUST be shown as such in the admin. *(US-1)*
- **FR-016**: No migration this feature adds may change or drop any existing version or
  acceptance. *(US-1)*
- **FR-017**: Every user-facing string this feature adds MUST be translatable, and none may state or
  imply that a site or a person is compliant. *(US-1, US-2)*
- **FR-018**: The documentation MUST explain what a translation is, that the version's own text
  governs, locking a version for translation, how to add and correct a translation in the admin and
  from code, every signal, and the permissions involved. *(US-2)*
- **FR-019**: A draft MUST be lockable for translation, as a distinct action behind the permission
  to publish, which makes it pending. A version MUST NOT be translatable while it is a draft.
  *(US-1)*
- **FR-020**: A pending version's wording and summary MUST NOT change by any route the package
  offers. Every route that refuses a change to a published version's wording MUST refuse it for a
  pending one. *(US-1)*
- **FR-021**: A pending version MUST have no number and no standing: it MUST NOT be in force,
  outstanding, accepted, compared, listed or shown on any page a visitor can reach, exactly as a
  draft. *(US-1)*
- **FR-022**: A pending version MUST be publishable, by the same action and permission as a draft,
  and MUST be able to be returned to draft behind the permission to publish. Returning it MUST
  return every translation of it that was put live to draft, keeping its wording. *(US-1)*
- **FR-023**: The package MUST send a signal after each change of state commits: a version locked
  for translation, a version returned to draft, a version published (with the version it
  superseded), a translation put live (with the wording it replaced), and a translation returned to
  draft. Each signal MUST name the object and the account that made the change, or none. *(US-2)*
- **FR-024**: A signal MUST NOT be sent for a change that is refused or rolled back, and a receiver
  that raises MUST NOT undo the change or stop the other receivers. *(US-2)*

### Key Entities

- **Version** (FS-001): gains one state, **pending**, between draft and published. Its own wording
  is in the site's main language, is what every acceptance points at, and governs.
- **Translation**: the wording of one pending or published version in one other language the site
  offers, with its summary. A version has at most one per language. It holds every wording it has
  had: the live one, and every earlier one with the times it was live, each with the account that
  put it live.
- **Acceptance** (FS-003): unchanged, and not read by this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every version in the demo, its stored fields and its acceptances are identical
  before and after translations are added and corrected.
- **SC-002**: For every translation in the demo that has been corrected, every wording it has had
  can be produced, with the times it was live.
- **SC-003**: Every route the package offers that would change a pending version's wording, or a
  translation's wording once it has been live, is refused, shown by tests that attempt each one.
- **SC-004**: An account holding only the permission to translate can take a translation from
  nothing to live, and cannot lock, return, publish, edit or discard any version.
- **SC-005**: A compliance editor can see, from one admin page, every pending or published version
  missing a translation into any offered language.
- **SC-006**: `makemessages` over the package picks up every string this feature adds.
- **SC-007**: Every page and query that ignores drafts today ignores pending versions too, shown by
  tests that put a pending version where a draft is tested now.
- **SC-008**: Each change of state sends exactly one signal, after it commits, and a refused or
  rolled-back change sends none.

## Clarifications

### Session 2026-11-06

- **Q**: Which languages can a version be translated into? → **A**: Those in the site's `LANGUAGES`
  other than `LANGUAGE_CODE` (FR-001). The package keeps no list of its own, and a version's own
  text is taken to be in the main language. Until a site sets `LANGUAGES` itself none are offered,
  because Django's built-in default lists every language it ships.
- **Q**: Can a live translation simply be overwritten when a mistake is found? → **A**: No (FR-008).
  A person may agree while reading the translation, and G2 says what they saw must be producible
  later. A correction replaces it from then on, and the earlier wording is kept.
- **Q**: Does a translation need a new version to be published? → **A**: No. That is the point of
  the feature. The version and its acceptances are never touched (FR-007).
- **Q**: Is the summary translated? → **A**: Yes, when the version has one (FR-002). A returning
  reader is shown the summary when asked to agree again, and #156 will show it in their language.
- **Q**: Can a translation be prepared before its version is published? → **A**: Yes, once the
  version is locked for translation (FR-019), and never while it is a draft. A draft's wording can
  still change, and a translation of wording that later changes would go live translating text that
  was never published.
- **Q**: Does a new version inherit the translations of the one it replaces? → **A**: No. Its
  wording is different, so a carried-over translation would translate text it does not contain.
- **Q**: Who may translate? → **A**: Holders of a permission of its own (FR-010). A translator is
  often an outside agency rather than the person who decides the wording.
- **Q**: Who may lock a version for translation, or return it to draft? → **A**: Holders of the
  permission to publish (FR-019, FR-022). Locking fixes the wording, which is the decision
  publishing makes.
- **Q**: What happens to translations when a pending version returns to draft? → **A**: Those put
  live return to draft with their wording (FR-022), so they are read again against the corrected
  version before they go live.
- **Q**: Is a second translation in a language that already has one refused? → **A**: There is no
  second translation to refuse: a wording added in that language is a correction of the one that
  exists (FR-003).
- **Q**: What does a project learn of these changes? → **A**: A signal for each change of state,
  sent after it commits (FR-023), so a project can, for instance, send a version that becomes
  pending to be translated.

## Assumptions

- FS-001 to FS-014 are delivered, and this spec is written against them as they stand on main.
  FS-001 and FS-002 are amended in the same pull request to name the pending state.
- A version's own wording is in the site's main language. Nothing records a language per version.
- Nothing a reader sees changes in this feature. Serving translations is #156.
- The package ships an English catalog only, as for every other string.
- Personal data: each live wording records the account that put it live, as a version records its
  publisher. That is one more place an account identifier is kept, and Article XIV's CHANGELOG entry
  names it. A signal passes the account to the project's own receivers, as `version_published`
  already does.
- The translation screens follow the admin's existing pages for writing and publishing a version.
  No requirement here fixes wording or appearance.
