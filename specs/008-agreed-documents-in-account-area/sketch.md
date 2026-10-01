# Sketch: what a person has agreed to, in their account area

A prototype of the page, built to be looked at before the implementation is planned. It has no
tests. The templates, the markup and the wording are what is being reviewed. The code behind them
is a stand-in that the plan may keep, change or rebuild.

## What exists

**The records the page reads**

- An acceptance names one person and one version, with the moment it was recorded. A person's
  acceptances are found with `Acceptance.objects.for_person(user)`, which matches on the same
  identifier the records were written under.
- A version carries its number, its publication date and its status, which is current or
  superseded once it is published. It leads to its document.
- A document carries its name, its slug and its kind. `Version.objects.current()` gives the
  version in force for each document.
- Nothing stored says "a newer version is in force that this person has not accepted". It is
  worked out by comparing the version in force with the versions the person accepted.
  `Document.objects.outstanding_for(user)` already answers the same question for every document,
  including ones the person never accepted, so it is wider than this page needs.
- A version's page is the document's address with `?version=<number>`. The version in force is the
  address without it.

**What is already there to build with**

- django-mvp's account area: the layout `mvp/account/base.html`, the menu `AccountCenterMenu`
  that an installed package appends to, and `MVPTemplateView` for the page title and the trail.
  The menu drops an entry whose address does not resolve.
- The document page already shows a replaced version under a warning alert with a small button
  to the current one. The list reuses that pattern for its own statement.

**Components that fit, and one that does not quite**

- `c-page`, `c-page.title`, `c-card`, `c-alert`, `c-badge` and a plain `table` cover the page.
- The empty state uses `c-page.list.empty`. It belongs to list views and draws its heading as a
  third-level heading directly under the page title. There is no general empty-state component.

## What the screens need from the code

- Every acceptance the signed-in person holds for a document people agree to, with the version's
  number and status, the document's name and slug, and the date of the acceptance.
- Those acceptances grouped by document, documents in name order, versions newest published first.
- For each listed document, its version in force and whether the person accepted it. When they did
  not, that version's number and publication date for the statement.
- A count of database queries that stays the same however long the list is.
- An address for the list that sits beside the document pages and cannot be taken by a slug.
- A menu entry in the account area that is present only when both the account area and the
  package's pages are mounted.
- A redirect to sign in for a visitor who is not signed in.

## What the sketch faked

- **The address.** The list answers at `agreed/` under the package's pages. Nothing yet refuses a
  document the slug `agreed`, so such a document would be unreachable instead of refused.
- **A project without the account area.** The page's trail links to the account area's landing
  page without checking it is mounted. In a project that mounts the package's pages and not the
  account area, the page would fail instead of being absent.
- **The view and its queries.** Written directly to make the page real, with no tests and no check
  on the number of queries.
- **Translations.** The new strings are marked for translation. No catalogue was updated.
- **Documentation.** None written.
- **The demo's history.** The seed command now publishes and accepts on past dates by replacing
  the clock while it runs, so the page shows dates spread over three years. Two documents and two
  accounts were added to reach every state. This is demo data only.

## What was ruled by eye

These are choices with no settled answer. Each is open to change in review.

- One card per document, in a single column no wider than comfortable reading width, in place of
  a two-column grid of cards.
- Under each document, a two-column table: the version, and the date it was agreed to. The
  publication date of each accepted version is left out.
- Each version carries a small label, "In force" or "Replaced", beside its number.
- The statement about a newer version sits inside the document's card, above its versions, as a
  soft warning with one button that opens the version in force.
- The statement names the newer version and the date it came into force.
- Dates are shown without the time of day.
- The page is titled "Documents you agreed to".
- The empty state reads "Nothing to show yet", followed by one line about when an entry appears.

### Changed in review

- The menu entry reads "Agreements", not "Agreed documents".
- The document page is two columns. The list of documents is the left column, in a card titled
  "Agreements". The document's title, its version menu and its wording are the right column, so
  the title no longer spans the full width. No line divides the columns. This changes the document
  page, which the specification left to issue #71.
- The card stays in view while the document scrolls: it stops 5rem below the top of the window,
  clear of the shell's top bar. The package ships a small stylesheet for that offset, because the
  shell's stylesheet has no utility for it. django-mvp-sphinx pins its "on this page" list the
  same way. The offset is a custom property a project can override.
