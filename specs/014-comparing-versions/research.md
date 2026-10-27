# Research — 014 Comparing two versions of a document

Written against main at 129adef, which carries the summaries of what changed (#132), and the
approved sketch.

## Planning notes

### N1 — The account area's alert is "far too cramped"

**Adopted.** Applied in the sketch's second round and approved. The alert's text and its buttons
sit in one column, buttons on their own line. The build keeps the template as approved.

### N2 — "Keep stuff like this generic. 'See what's changed' is perfectly adequate."

**Adopted.** Every link that opens a comparison uses that one string, with no version number. The
comparison names both versions itself (FR-007), so nothing is lost. Recorded as D12.

### N3 — No comparison on the staff page, and "version <version>" links to the version in the admin

**Adopted, with one condition.** The staff page offers no comparison. Each acceptance's version
text links to that version's admin change page. The page is open to anyone holding
`produce_disclosure` alone (ADR 0011), and such a person usually cannot view versions in the admin.
A link that answers "403" is a defect, so the link is drawn only when the person reading may view
versions (`mvp_compliance.view_version`), and the text stays plain otherwise. Showing the whole
document there is a separate issue and is not touched.

## The sketch

### What the screens need from the code

| Need | How it is met |
|---|---|
| A word-by-word comparison of two stored HTML texts, keeping structure, keeping a removed paragraph or list item whole, well under a second for 15,000 words | `Comparison` in `mvp_compliance/comparison.py`, built on `difflib.SequenceMatcher`, in two passes (below) |
| Both versions with their dates in force, the document's versions for the pickers | One query: `document.versions.published().with_replaced_at()`, already used by the document's page |
| The version in force on a document's page, for the replaced-version alert | Already in that query's result: the version with no `replaced_at`. No extra query |
| The newest version a person accepted, on the account area's list | Already loaded: the acceptances are ordered newest first per document (`of_agreed_documents`) |
| The same on the page asking to agree, in one query for the page | A query over the person's acceptances of the listed documents, ordered newest first, kept in `get_entries` beside #132's query |
| On the staff page, each acceptance's version | `AcceptanceEntry` gains `version_id`. `produce()` already loads the version, so no query is added |

### What the sketch faked, and what becomes of it

| Faked | Becomes |
|---|---|
| The comparison has no tests and its thresholds were tuned by eye | Tests per FR-002 to FR-006 and FR-009, with the thresholds named as class attributes |
| The staff page's link is added by wrapping entries, with an extra query | `AcceptanceEntry.version_id`, and the template reverses the admin address. `with_version_links` is deleted |
| The agree page reads earlier acceptances in `get_context_data` | Moved into `get_entries`, so the entries carry it like `changes` |
| The stylesheet is linked from the comparison page only | Kept: the marks occur nowhere else |
| New strings are not in the catalogue | Added to `locale/en/LC_MESSAGES/django.po`, and the page-strings test lists the new template |
| A bare `compare/` address compares the version in force with the one before it | Removed. FR-009 asks for an address built from the two versions, and nothing links to a bare one. Both numbers are required, and either missing answers "not found" |

## The comparison

**Two passes.** A single `SequenceMatcher` over every token of two 15,000-word texts did not finish
in two minutes in the sketch: its cost grows with the product of the lengths. The sketch's two
passes answer in about 0.2 seconds:

1. Each text is split into its top-level elements (a heading, a paragraph, a list item; a list is
   opened into its items). The elements are compared as whole strings, whitespace collapsed. Equal
   runs are copied from the newer version.
2. Within a range that differs, each newer element is paired with the first older element at least
   half alike by its words, and those two are compared word by word. An element with no partner is
   added or removed whole, with its own markup.

**Pathological input.** Two entirely different texts give one range that differs, and pairing
then compares every element with every other. `SequenceMatcher.real_quick_ratio()` and
`quick_ratio()` are upper bounds of `ratio()` that cost almost nothing, so they are checked first
and the full ratio is computed only when they reach the threshold. The test for SC-004 uses two
texts that share nothing as well as two that differ throughout.

**Output safety (FR-006, Article V).** The output is made only of tokens taken from the two stored
texts, which passed the sanitiser at publication, plus `<ins>`, `<del>` and a hidden `<span>`
holding a translated label that is escaped. The sanitiser's allow list contains neither `ins` nor
`del`, so a mark can never be confused with stored content. A removed word's tags are dropped and
an added word's tags kept outside the mark, so no mark ever spans a tag boundary and every element
stays balanced. The tests assert that the output, with the marks removed, holds no tag that is not
in one of the two inputs.

**Words.** A word is a run of non-space characters with its punctuation, as the sketch has it.
Character-level marks were ruled out (D5). Whitespace between two changed words is folded into the
change, so a rewritten phrase is one removal and one addition.

## Addresses

`<slug>/compare/?from=<number>&to=<number>`, named `mvp_compliance:comparison`. It is nested under
the document's slug, so no document slug can collide with it, and FR-021's reserved-slug clause is
met by the route's shape. The order of the two numbers does not matter (FR-008).

## Reconciling with #132

The page asking to agree shows the summaries of what changed (#132) and the comparison link side
by side in each row: the link sits under "View document in full", the summaries under it. Neither
reads the other. Both are computed in `get_entries`.

## Documentation

`docs/pages.md` gains a section on comparing versions: what it shows, where the package offers
it, its address, how to link to it and its template. The README's list of pages and the CHANGELOG
are updated. The specs that describe the pages gaining a link are updated to read as current:
FS-004 (the version link), FS-006, FS-008 and FS-009.

## What already exists

```
word-by-word comparison            · 4, standard library · difflib.SequenceMatcher
HTML tokenising                    · 7, new · searched mvp_compliance/, nh3 (only sanitises), markdown (only renders), django.utils.html (escapes only); a regular expression over sanitised HTML is enough
escaping the hidden label          · 4, Django · django.utils.html.escape
the comparison page's shell        · 2, this repo · DocumentView's template, its side list and actions slot
version pickers                    · 3, package · c-mvp.dropdown, as the version switcher uses it
the version card                   · 3, package · c-mvp.card and daisyUI's list, as the agree page uses them
"nothing to mark" alert            · 3, package · c-alert
the marks' look                    · 7, new · the prebuilt stylesheet has no rule for ins or del and no colour-with-opacity utility (checked in mvp/static/css/django-mvp.css); a nine-line stylesheet using the theme's colours
versions with dates in force       · 2, this repo · VersionQuerySet.published().with_replaced_at()
newest accepted version, account   · 2, this repo · AgreedDocumentsView.get_entries, already ordered newest first
newest accepted version, agree     · 2, this repo · Acceptance.objects.for_person
admin address of a version         · 4, Django · the admin's named URL admin:mvp_compliance_version_change
permission to view a version       · 4, Django · {{ perms.mvp_compliance.view_version }}
```
