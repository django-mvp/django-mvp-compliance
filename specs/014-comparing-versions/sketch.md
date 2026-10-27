# Sketch — 014 Comparing two versions of a document

The screens for FS-014, built on the feature's branch and reviewed on the running demo before the
work is planned. Nothing here is tested. The build keeps the screens that are approved and rebuilds
the code behind them test-first.

## What exists

- **Version** stores `html`, rendered and sanitised at publication, with `number` and
  `published_at`. `published().with_replaced_at()` adds when each was replaced, in one query. That
  is everything a comparison needs to read. Drafts have no number, so they cannot be named.
- **The document's page** (`DocumentView`, `document_detail.html`) already has the actions slot with
  the version switcher, the replaced-version alert, and the side list of documents. The comparison
  page reuses all three.
- **The account area's list** (`AgreedDocumentsView`) already works out, in one query, the version
  in force a person has not accepted (`newer`), and lists their acceptances newest first. The newest
  one is the older side of their comparison.
- **The page asking to agree** (`AgreementView`, `<c-compliance.outstanding>`) has a row per
  outstanding document with a link that opens the version in a new tab. It knows nothing about
  earlier acceptances.
- **The staff page** (`DisclosureAdmin`, `records.produce`) gives each acceptance as a frozen
  `AcceptanceEntry` holding the document's name and the version's number only, with no slug and
  no version in force.
- **Components**: `c-mvp.dropdown`, `c-button`, `c-alert`, `c-mvp.card`, the daisyUI `list`. Nothing
  in the prebuilt stylesheet styles `<ins>` and `<del>`, and no colour-with-opacity utility is in
  it, so the marks need a small stylesheet of the package's own.
- No planning notes exist for this feature.

## What the screens need from the code

- The comparison page needs a word-by-word comparison of two stored HTML texts that keeps the
  newer version's structure, keeps a removed paragraph or list item whole with its own markup, and
  answers in well under a second for two texts of about 15,000 words.
- The comparison page needs both versions with their dates in force, and the document's published
  versions for its two pickers.
- The document's page needs the version in force, for the replaced-version alert's comparison
  button.
- The account area's list needs, for each document with a newer version in force, the newest
  version the person accepted.
- The page asking to agree needs, for each outstanding document, the newest version of it the
  person accepted, in one query for the whole page.
- The staff page needs, for each acceptance, the primary key of the version accepted, to link to its admin page.

## What the sketch faked

- The comparison (`mvp_compliance/comparison.py`) is a first working version with no tests. It
  matches top-level elements, opens lists item by item, pairs changed elements by how alike their
  words are (half or more), and folds a space left unchanged between two changes into them.
  The thresholds are guesses tuned on the demo.
- The staff page's link from each version number to its admin page is added by wrapping each
  `AcceptanceEntry` in a plain object in `DisclosureAdmin.with_version_links`, with one extra query
  for the versions named. The answer produced (`records.produce`) is unchanged, and so is the copy a
  person downloads.
- The page asking to agree reads the newest acceptance per document with a separate query in
  `get_context_data`, outside `get_entries`.
- The comparison stylesheet (`static/mvp_compliance/comparison.css`) is linked from the comparison
  page only.
- Strings in the comparison page and the marks are wrapped for translation but not in the catalogue.
- Two notices were added to the demo for comparing: an accessibility statement in three versions
  (a word changed, a list item added and one removed, a link changed, a section moved to the top),
  and an open-source licences notice of about 15,000 words in two versions. One account,
  `lapsed.user`, accepted early versions of two documents and nothing since.

## What was ruled by eye

Taste calls made for round 1, each open to change:

- The comparison is its own page, `/<document>/compare/?from=<number>&to=<number>`, next to the
  document's page. Without `from` and `to` it compares the version in force with the one before it.
- Its actions are two pickers, "From v…" (plain) and "To v…" (primary), so either side can change
  without going back to the document.
- Above the text, a card names the older and newer version with the dates each was in force and a
  link to read each in full. A one-line key under it shows what an addition and a removal look like.
- An addition is underlined on a green tint and a removal struck through on a red tint, in the
  theme's success and error colours.
- The document's page has a comparison dropdown beside the version switcher, listing the other
  versions. A replaced version's alert gains a comparison button before "View current version".
- The account area's alert about a newer version gains a comparison button before "Read v…".
- On the page asking to agree, a second link under "View document in full" opens the comparison in
  a new tab like the first.

Ruled in review (round 2):

- Every link to a comparison reads "See what's changed", with no version numbers: the document
  page's menu button, the replaced-version alert, the account area's alert and the page asking to
  agree.
- The account area's alert puts its buttons on their own line under the text.
- The staff page offers no comparison. Each acceptance's "version …" text links to that version's
  admin page instead. Showing the whole document there is left to a separate issue.
