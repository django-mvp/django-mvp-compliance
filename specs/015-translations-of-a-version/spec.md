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
translation covers the version's wording and its summary. It can be started while the version is
still a draft, and it goes live only once the version itself is published, so a site can launch a
version and its translations on the same day or add them weeks later.

A live translation can be corrected. A correction replaces the wording readers will be served from
then on. The wording it replaces is kept, with the dates it was live, because a person may have
read it when they agreed and what they saw must still be producible later (G2).

The version itself never changes. Its own text is in the site's main language, it is still what
every acceptance points at, and it is the text that governs. A translation is an aid to reading it.

Translating is a permission of its own, separate from publishing versions, because the translator
is often not the person who decides the wording. The admin shows, for each published version, which
of the site's languages it has a live translation in and which it lacks.

A developer can also add and correct translations from code, the way a version can already be
published from code, for a site that keeps its translations in files and loads them on deploy.

Some things stay out of this feature:

- What a reader is served, on a document's page and on the page asking them to agree, is issue
  #156. Until it lands, nothing a reader sees changes: a live translation is held and listed in the
  admin and shown nowhere else.
- Whether an acceptance records which translation was on screen is issue #156.
- Comparing two translations, or a translation with its version, is not part of R7.
- The email announcing a new version (FS-005), the copy a person downloads (FS-012) and the page
  staff use to produce everything held about a person (FS-004) are unchanged.
- The package ships no list of languages and no machine translation. Every translation is written
  by a person.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Translating a version, and correcting the translation later (Priority: P1)

The privacy policy's version 2026.2 went into force last month. The site also offers German. A
translator who can translate documents but not publish versions opens 2026.2 in the admin, sees
that it has no German translation yet, and writes one, including its summary. They preview it, the
way a version is previewed, and put it live. Version 2026.2 is exactly as it was, and so is every
acceptance of it.

Three weeks later a reader points out a mistranslated clause. The translator corrects it and puts
the correction live. From then on the corrected wording is the German translation. The wording it
replaced is still on record, with the dates it was live.

**Why this priority**: It is the feature. Without it no translation exists, and #156 has nothing to
show.

**Independent Test**: With German among the site's languages, publish a version, then as an account
holding only the permission to translate, write a German translation, preview it and put it live.
Check the version's wording, summary, number and stored HTML are unchanged, and its acceptances
untouched. Correct the translation and put the correction live. Check the corrected wording is the
live one, and the earlier wording is still held with the dates it was live.

**Acceptance Scenarios**:

1. **Given** a published version and a language the site offers other than its main one, **When**
   someone with the permission to translate writes a translation of the version in that language,
   **Then** it is held as not yet live, and nobody without access to the admin's documents can see
   it.
2. **Given** a translation that is not yet live, **When** it is previewed, **Then** it is shown as
   it will be served, from the same rendering a version goes through at publication.
3. **Given** a translation that is not yet live, **When** it is put live, **Then** its wording is
   rendered and stored at that moment, and the stored wording is what is served from then on.
4. **Given** a version with live translations, **When** it is read, **Then** its wording, summary,
   number, stored HTML, publication date and publisher are exactly as before any translation
   existed, and no acceptance of it has changed.
5. **Given** a live translation, **When** it is corrected and the correction is put live, **Then**
   the corrected wording is the live translation from that moment, and the wording it replaced is
   kept unchanged, with the times it went live and was replaced.
6. **Given** a live translation, **When** anybody tries to change its stored wording by any route
   the package offers, other than putting a correction live, **Then** the change is refused.
7. **Given** a version, **When** a translation is written for it, **Then** the translation can hold
   a translated summary as well as the translated wording, and a version with no summary has none
   to translate.
8. **Given** a draft version, **When** a translation of it is written and put live, **Then** it
   does not become live until the version is published, and becomes live when the version is.
9. **Given** a draft version with a translation, **When** the draft is discarded, **Then** its
   translation is discarded with it.
10. **Given** a language that the site does not offer, or the site's main language, **When** a
    translation in it is attempted, **Then** it is refused.
11. **Given** a version that already has a translation in a language, **When** a second translation
    in the same language is attempted, **Then** it is refused. The existing one is corrected
    instead.
12. **Given** an account with the permission to translate and not the permission to publish
    versions, **When** it uses the admin, **Then** it can write, preview, put live and correct
    translations, and cannot publish, edit or discard a version.
13. **Given** an account without the permission to translate, **When** it tries to put a
    translation or a correction live, **Then** it is refused.
14. **Given** a published version, **When** it is viewed in the admin, **Then** it shows which of
    the site's languages it has a live translation in and which it has none in, and the list of
    versions can be narrowed to those missing a translation.
15. **Given** a notice, **When** its version is translated, **Then** it is translated exactly as a
    document people agree to.
16. **Given** a translation put live or corrected, **When** it is looked at later, **Then** it
    names the account that put it live, kept as the publisher of a version is kept, including after
    that account is removed.

---

### User Story 2 - A developer adds translations from code (Priority: P3)

A site keeps its translated documents in its repository and loads them on deploy. Its developer
calls the package from a data migration or a management command to add the German translation of
the version in force, and later to put a correction live, with the same results as doing it in the
admin.

**Why this priority**: The admin covers every site. This saves a site that already manages its
translations as files from retyping them, and it matches publishing a version from code, which the
package already offers.

**Independent Test**: From code, add a translation to a published version and put it live, then
put a correction live. Check the results are the same as doing it in the admin, including the kept
earlier wording, and that a translation in a language the site does not offer raises.

**Acceptance Scenarios**:

1. **Given** a version, **When** a developer adds a translation in an offered language from code
   and puts it live, **Then** the result is the same as doing it in the admin, with nobody named as
   having put it live unless the call names an account.
2. **Given** a live translation, **When** a developer puts a correction live from code, **Then**
   the earlier wording is kept exactly as when it is corrected in the admin.
3. **Given** a call that the admin would refuse, such as a language the site does not offer or a
   second translation in one language, **When** it is made from code, **Then** it raises the
   package's own exception, and nothing is written.
4. **Given** a developer reading the documentation, **When** they look for how to translate a
   version, **Then** it explains what a translation is, what governs, how to add and correct one in
   the admin and from code, and the permission it needs.

---

### Edge Cases

- A language is removed from the site's `LANGUAGES` after translations into it were put live. They
  are kept, never deleted, and the admin shows them as in a language the site no longer offers.
- The site's main language is changed after translations exist. Nothing is rewritten. A translation
  that now shares the main language is kept and flagged in the admin.
- A version is superseded. Its translations stay, and can still be corrected, because a person
  holding an acceptance of it may still read it.
- A translation is put live while its version is in force, and a new version is published the next
  day. The new version starts with no translations. Nothing is carried over from the one it
  replaces.
- Two people correct the same translation at once. Both corrections are kept, the later one put
  live is the live translation, and neither is lost.
- A translated wording contains markup the sanitiser does not allow. It is removed exactly as for a
  version.
- A site offers only one language. Nothing about translations appears in the admin.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A compliance editor MUST be able to write a translation of a version into any language
  in the site's `LANGUAGES` other than its main language (`LANGUAGE_CODE`), from the admin, without a
  deploy or a migration. *(US-1)*
- **FR-002**: A translation MUST hold the translated wording of a version and MAY hold a translated
  summary. *(US-1)*
- **FR-003**: A version MUST have at most one translation per language. *(US-1, US-2)*
- **FR-004**: A translation MUST be previewable before it is live, through the same rendering a
  version goes through. *(US-1)*
- **FR-005**: Putting a translation live MUST render and store its HTML at that moment, and the
  stored HTML MUST be what is served afterwards. Markdown MUST NOT be rendered at request time.
  *(US-1)*
- **FR-006**: A translation of a draft MUST NOT be live until the version is published. Discarding
  the draft MUST discard its translations. *(US-1)*
- **FR-007**: Writing, putting live or correcting a translation MUST NOT change any field of its
  version, or any acceptance. *(US-1, US-2)*
- **FR-008**: Once a wording of a translation has been live, it MUST never be changed or deleted by
  any route the package offers. A correction MUST be a new wording that replaces it, and the
  wording it replaces MUST be kept with the times it went live and was replaced. *(US-1, US-2)*
- **FR-009**: Each live wording of a translation MUST record the account that put it live, kept as a
  version's publisher is kept, or record that nobody was named. *(US-1, US-2)*
- **FR-010**: Translating MUST be a permission of its own, separate from publishing a version, and
  putting a translation or a correction live MUST require it. The permission MUST NOT allow
  publishing, editing or discarding a version. *(US-1)*
- **FR-011**: The admin MUST show, for each published version, which offered languages it has a live
  translation in and which it has none in, and MUST let the list of versions be narrowed to those
  missing a translation. *(US-1)*
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
  governs, how to add and correct one in the admin and from code, and the permission it needs.
  *(US-2)*

### Key Entities

- **Version** (FS-001): unchanged. Its own wording is in the site's main language, is what every
  acceptance points at, and governs.
- **Translation**: the wording of one version in one other language the site offers, with its
  summary. A version has at most one per language. It holds every wording it has had: the live one,
  and every earlier one with the times it was live, each with the account that put it live.
- **Acceptance** (FS-003): unchanged, and not read by this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every version in the demo, its stored fields and its acceptances are identical
  before and after translations are added and corrected.
- **SC-002**: For every translation in the demo that has been corrected, every wording it has had
  can be produced, with the times it was live.
- **SC-003**: Every route the package offers that would change a wording once it has been live is
  refused, shown by tests that attempt each one.
- **SC-004**: An account holding only the permission to translate can take a translation from
  nothing to live, and cannot publish, edit or discard any version.
- **SC-005**: A compliance editor can see, from one admin page, every published version missing a
  translation into any offered language.
- **SC-006**: `makemessages` over the package picks up every string this feature adds.

## Clarifications

### Session 2026-11-06

- **Q**: Which languages can a version be translated into? → **A**: Those in the site's `LANGUAGES`
  other than `LANGUAGE_CODE` (FR-001). The package keeps no list of its own, and a version's own
  text is taken to be in the main language.
- **Q**: Can a live translation simply be overwritten when a mistake is found? → **A**: No (FR-008).
  A person may agree while reading the translation, and G2 says what they saw must be producible
  later. A correction replaces it from then on, and the earlier wording is kept.
- **Q**: Does a translation need a new version to be published? → **A**: No. That is the point of
  the feature. The version and its acceptances are never touched (FR-007).
- **Q**: Is the summary translated? → **A**: Yes, when the version has one (FR-002). A returning
  reader is shown the summary when asked to agree again, and #156 will show it in their language.
- **Q**: Can a translation be prepared before its version is published? → **A**: Yes, and it goes
  live with the version (FR-006), so a site can launch a version and its translations together.
- **Q**: Does a new version inherit the translations of the one it replaces? → **A**: No. Its
  wording is different, so a carried-over translation would translate text it does not contain.
- **Q**: Who may translate? → **A**: Holders of a permission of its own (FR-010). A translator is
  often an outside agency rather than the person who decides the wording.

## Assumptions

- FS-001 to FS-014 are delivered, and this spec is written against them as they stand on main.
- A version's own wording is in the site's main language. Nothing records a language per version.
- Nothing a reader sees changes in this feature. Serving translations is #156.
- The package ships an English catalog only, as for every other string.
- Personal data: each live wording records the account that put it live, as a version records its
  publisher. That is one more place an account identifier is kept, and Article XIV's CHANGELOG entry
  names it.
- The translation screens follow the admin's existing pages for writing and publishing a version.
  No requirement here fixes wording or appearance.
