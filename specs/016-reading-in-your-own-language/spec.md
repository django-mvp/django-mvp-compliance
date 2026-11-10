# Feature Specification: Reading a document in your own language

**Feature Branch**: `016-reading-in-your-own-language`

**Created**: 2026-11-10

**Status**: Draft

**Serves**: G4, G2 · **Roadmap**: R7 · **Issue**: #156

**Input**: A reader should see a legal document in their own language wherever a translation
exists. That covers the document's page and the page that asks them to agree to it. They should be
able to tell they're reading a translation, and get to the original text that governs from there.
Agreeing while reading a translation still records agreement to the version itself, because that
is what the person is bound by. A reader in a language with no translation sees the original, just
as they do today.

## Scope

FS-015 lets a compliance editor write translations of a version and put them live. Nothing a reader
sees has used them so far. This feature serves them.

A reader's language is the one the site is already showing them: the language Django has active
for the request. The package adds no language switcher and no middleware. How a person picks a
language is the host project's choice.

When a live translation exists in the reader's language, the document's page shows it in place of
the original. That holds for the version in force and for every superseded version. The page asking
a person to agree shows the summaries of what changed in their language too. Wherever translated
text is shown, the page tells the reader three things: that they are reading a translation, that
the original governs, and how to read the original, which is one step away. The document's address
never changes between the two.

A person who agrees while the page is shown in translation agrees to the version, as anybody else
does. What they agree to is the version's original text. The acceptance also records what they were
shown: the language, and the notice that told them they were reading a translation and pointed them
to the original. That notice is kept in the words the person saw, and a later change to the site's
templates or translation catalogues does not change it. Staff producing everything held about a
person, and the person's own copy, can then show what the person was shown when they agreed: the
translated wording, and the notice that directed them to the original.

A reader in a language with no live translation sees the original, exactly as today. So does every
reader on a site that offers one language or has not set `LANGUAGES`.

Some things stay out of this feature:

- Writing, locking, putting live and correcting translations are FS-015, unchanged.
- Comparing versions keeps comparing the originals. Comparing translations is not part of R7.
- The email announcing a new version (FS-005) stays in the original.
- A document's name is not translated by FS-015, so it stays as it is.
- The package ships no language switcher.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reader reads a document in their own language (Priority: P1)

A site offers English and German, and its privacy policy has a live German translation. A reader
browsing the site in German opens the privacy policy. They see the German wording, with a notice
saying it is a translation, that the English original is the text that governs, and a link to it.
They follow the link, read the original at the same address, and can return to the German. A reader
browsing in French, for which there is no translation, sees the English original with no notice.

**Why this priority**: It is the feature. Without it translations are held and never read.

**Independent Test**: With German and French offered and a live German translation of the version
in force, open the document's page in German and check the stored translated HTML is served, with
the notice and a link to the original. Follow the link and check the version's own stored HTML is
served at the same address. Open the page in French and check the original is served with no notice.

**Acceptance Scenarios**:

1. **Given** a version with a live translation in the reader's language, **When** the reader opens
   the document's page for it, **Then** the translation's stored HTML is served in place of the
   version's, and nothing is rendered from Markdown at request time.
2. **Given** a page showing a translation, **When** it is read, **Then** it tells the reader that
   the text is a translation, that the original governs, and offers the original one step away.
3. **Given** a page showing a translation, **When** the reader asks for the original, **Then** the
   version's own stored HTML is served at the same document address, and the reader can return to
   the translation.
4. **Given** a reader in a language with no live translation of the version shown, **When** they
   open the document's page, **Then** the original is served with no notice, exactly as before this
   feature.
5. **Given** a superseded version with a live translation, **When** a reader in that language opens
   it, **Then** the translation is served with its notice, and the page still says the version has
   been replaced.
6. **Given** a reader whose language is a regional variant, such as `de-at`, with no translation in
   that variant, **When** a translation in the general language (`de`) is live, **Then** that
   translation is served.
7. **Given** a translation put live on a pending version, or in a language the site no longer
   offers, or in the main language, **When** a reader opens the page, **Then** it is not served.
8. **Given** a translation that was corrected, **When** a reader opens the page, **Then** the
   wording live now is served, never an earlier one.
9. **Given** a page showing a translation, **When** it is read by a browser or assistive technology,
   **Then** the translated text is marked with its language.
10. **Given** a notice, **When** it has a live translation, **Then** it is served exactly as a
    document people agree to.
11. **Given** a site that offers one language or has not set `LANGUAGES`, **When** any document page
    is opened, **Then** it is exactly as before this feature.

---

### User Story 2 - A person agrees while reading in their own language (Priority: P1)

A new version of the terms is published with a German translation and a German summary. A
signed-in person browsing in German is asked to agree. The page shows the summary of what changed
in German, with the notice that the German is a translation, the English original governs, and how
to read it. They agree. The acceptance is of the version itself, and it records that they were
shown German and the notice they were shown, in the words they saw.

**Why this priority**: Most people meet a document on the page asking them to agree. A translation
shown there without the notice on record leaves the site unable to show that the person was told
what governs.

**Independent Test**: With a live German translation and summary of the version in force, open the
agreement page in German and check the summary is the German one and the notice is shown. Agree,
and check the acceptance points at the version, records German, and records the notice's text as it
appeared on the page. Change the notice's wording in the catalogue and check the recorded text is
unchanged.

**Acceptance Scenarios**:

1. **Given** an outstanding document whose versions have live translations in the person's
   language, **When** the agreement page is drawn, **Then** each summary shown is the translated one
   where it exists, and the link to the document leads to its page in that language.
2. **Given** an agreement page showing any translated text, **When** it is read, **Then** it tells
   the person that the text is a translation, that the original governs, and how to read the
   original.
3. **Given** a version whose translation has no translated summary, **When** its summary is shown
   in that language, **Then** the original summary is shown and marked as untranslated.
4. **Given** a person who agrees on a page showing translated text, **When** the acceptance is
   recorded, **Then** it is an acceptance of the version, exactly as for any reader, and it also
   records the language shown and the full text of the translation notice the person was shown.
5. **Given** a recorded translation notice, **When** the site's templates or translation catalogues
   change later, **Then** the recorded text is unchanged.
6. **Given** a person who agrees on a page showing only the original, **When** the acceptance is
   recorded, **Then** it records no language and no notice, and reads as given on the original.
7. **Given** an agreement page drawn with a translated wording, **When** that translation is
   corrected, put live or returned to draft before the person submits, **Then** nothing is recorded
   for that document and the page is drawn again as changed, as it is when a version changes.
8. **Given** an acceptance recorded on a translated page, **When** it is read later, **Then** the
   translated wording and summary that were live at the moment it was given can be identified
   exactly.
9. **Given** acceptances recorded before this feature, **When** the feature's migration runs,
   **Then** none of them is changed, and each reads as given on the original.

---

### User Story 3 - Staff produce what a person was shown when they agreed (Priority: P2)

A person who agreed in German disputes, a year later, what they agreed to. Staff produce everything
held about them. For that acceptance the page shows the version agreed to, that it was given on a
page shown in German, the German wording and summary live at that moment, and the notice the person
was shown telling them the English original governed. The person's own copy shows the same.

**Why this priority**: The record from US-2 is only evidence if somebody can produce it. It comes
after the reader's stories because nothing is recorded until they exist.

**Independent Test**: Record an acceptance on a page shown in German, then correct the German
translation. Produce everything held about the person and check the acceptance shows the language,
the wording live when it was given (not the correction), and the recorded notice text. Download the
person's copy and check it carries the same.

**Acceptance Scenarios**:

1. **Given** an acceptance given on a translated page, **When** staff produce everything held about
   the person, **Then** it shows the version agreed to, the language shown, the translated wording
   and summary live at that moment, and the recorded notice text.
2. **Given** an acceptance given on a translated page, **When** the person downloads their copy,
   **Then** it carries the same, in its readable page and in its data for other software.
3. **Given** an acceptance given on the original, **When** either is produced, **Then** it is shown
   exactly as before this feature.
4. **Given** a translation corrected after the acceptance, **When** the acceptance is produced,
   **Then** the wording shown is the one live when it was given, never the correction.

---

### Edge Cases

- A reader's language is the main language. They see the original with no notice.
- A translation is put live after a person drew the agreement page in that language with only the
  original. That is a change on the page, handled as in US-2 scenario 7.
- A version's translation is in a language later removed from `LANGUAGES`. It is no longer served,
  and acceptances already given in it still produce what was shown.
- A person agrees in German, then later reads the same version in French with no French
  translation. They see the original. Their acceptance is unchanged.
- A project overrides the agreement view's `record_agreed()`. The documentation says what it must
  pass on for the language and notice to be recorded.
- The person's language changes between drawing the agreement page and submitting it. What is
  recorded is what the submitted page showed.
- A project's own templates override the document or agreement page. The translation notice is
  provided by the package, and the documentation says what an override must keep.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The reader's language MUST be the language Django has active for the request. The
  package MUST NOT add middleware or a language switcher. *(US-1, US-2)*
- **FR-002**: The document's page MUST serve the stored HTML of the live translation of the shown
  version in the reader's language, when one exists, for the version in force and for superseded
  versions. Markdown MUST NOT be rendered at request time. *(US-1)*
- **FR-003**: When no live translation exists in the reader's language, or in its general language
  for a regional variant, the original MUST be served, with no notice. *(US-1)*
- **FR-004**: Only a translation that is live, of a published version, in a language the site
  offers other than its main language, MUST be served. *(US-1, US-2)*
- **FR-005**: Every page showing translated text MUST tell the reader that it is a translation,
  that the original governs, and how to reach the original. *(US-1, US-2)*
- **FR-006**: The original MUST be reachable from a translated page in one step, at the same
  document address, and the reader MUST be able to return to the translation. *(US-1)*
- **FR-007**: Translated text MUST be marked with its language. *(US-1)*
- **FR-008**: The agreement page MUST show each version's translated summary in the person's
  language where one exists, and MUST mark an original summary shown on a translated page as
  untranslated. *(US-2)*
- **FR-009**: An acceptance MUST always be of the version. A translation MUST never be what an
  acceptance points at, and MUST never be presented as the governing text (FS-015 FR-013).
  *(US-2)*
- **FR-010**: An acceptance given on a page showing translated text MUST record the language shown
  and the full text of the translation notice the person was shown, in the words shown. *(US-2)*
- **FR-011**: A recorded notice MUST NOT change when the site's templates, settings or translation
  catalogues change, and MUST NOT be editable by any route the package offers, as an acceptance is
  not. *(US-2)*
- **FR-012**: An acceptance given on a page showing only the original MUST record no language and
  no notice. *(US-2)*
- **FR-013**: When a translation shown on the agreement page changes before the person submits, the
  page MUST record nothing for that document and MUST be drawn again as changed. *(US-2)*
- **FR-014**: From an acceptance given on a translated page, the translated wording and summary live
  at the moment it was given MUST be identifiable exactly. *(US-2, US-3)*
- **FR-015**: The page staff use to produce everything held about a person (FS-004), and the
  person's copy (FS-012), MUST show for each acceptance given on a translated page the language, the
  translated wording and summary live when it was given, and the recorded notice. *(US-3)*
- **FR-016**: No migration this feature adds may change or drop any existing version, translation
  or acceptance. Existing acceptances MUST read as given on the original. *(US-2)*
- **FR-017**: A site that offers one language, or has not set `LANGUAGES`, MUST see every page and
  record exactly as before this feature. *(US-1, US-2, US-3)*
- **FR-018**: Every user-facing string this feature adds MUST be translatable, and none may state
  or imply that a site or a person is compliant. *(US-1, US-2, US-3)*
- **FR-019**: The documentation MUST explain how a reader's language is chosen, what is served and
  when, the translation notice and what is recorded with an acceptance, how it is produced later,
  and what a project overriding the pages or `record_agreed()` must keep. *(US-1, US-2, US-3)*

### Key Entities

- **Version** (FS-001): unchanged. Its own wording is the original, and governs.
- **Translation** (FS-015): unchanged. Its live wording is what a reader in its language is served.
- **Acceptance** (FS-003): still points at a version. Given on a translated page, it also holds the
  language shown and the text of the translation notice shown, both fixed once recorded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every live translation in the demo, a reader in its language is served the stored
  translated HTML with the notice, and a reader in any other language the original without it.
- **SC-002**: Every acceptance recorded on a translated page in the demo produces, on the staff page
  and in the person's copy, the language, the wording live when it was given and the notice shown.
- **SC-003**: Changing the notice's wording in the translation catalogue changes no recorded notice,
  shown by a test.
- **SC-004**: Every acceptance existing before the migration is identical after it.
- **SC-005**: With one language offered, the document and agreement pages and the acceptance record
  are as on main, shown by the existing tests passing unchanged.
- **SC-006**: The document page's query count is the same whether or not a translation is served.
- **SC-007**: `makemessages` over the package picks up every string this feature adds.

## Clarifications

### Session 2026-11-10

- **Q**: How is the reader's language decided? → **A**: Django's active language for the request
  (FR-001). Choosing it is the host project's job, through `LocaleMiddleware` or its own means.
- **Q**: Is recording the language enough to show the person was directed to the original? → **A**:
  No (FR-010, FR-011). The maintainer ruled that the record must hold the notice itself, in the
  words shown, because a stored language says nothing about whether the person was told the
  original governs. Notice text from a catalogue can change later, so the text shown is kept.
- **Q**: What is recorded when the page showed only the original? → **A**: Nothing beyond what is
  recorded today (FR-012). Existing acceptances read the same way (FR-016).
- **Q**: What if a translation is corrected between drawing the agreement page and submitting it?
  → **A**: Nothing is recorded for that document, and the page is drawn again as changed (FR-013),
  as for a version that changes. Otherwise the record could point at wording the person never saw.
- **Q**: Which translated wording does an acceptance stand for? → **A**: The one live at the moment
  it was given (FR-014). FS-015 keeps every wording with the times it was live, so this is exact.
- **Q**: Do the staff page and the person's copy show any of this? → **A**: Yes (FR-015). A record
  nobody can produce is not evidence, and G2 requires it to be producible.
- **Q**: Are regional variants served the general language's translation? → **A**: Yes (US-1
  scenario 6), as Django falls back from `de-at` to `de`.
- **Q**: Is a translation in a language no longer offered served? → **A**: No (FR-004). It stays in
  the admin, as FS-015 keeps it, and acceptances given in it still produce what was shown.

## Assumptions

- FS-001 to FS-015 are delivered, and this spec is written against them as they stand on main.
- A version's own wording is in the site's main language (FS-015).
- The agreement page shows each document's name, its summaries and a link to its page, not its full
  wording. The wording a person agreed under is the one that link led to, identified through FS-015's
  history.
- The package ships an English catalogue only, as for every other string.
- Personal data: the language shown and the notice text are added to an acceptance. Neither
  identifies a person beyond the acceptance that already does, and Article XIV's CHANGELOG entry
  names them.
- The notice's look follows the page's existing alerts. No requirement here fixes wording or
  appearance.
