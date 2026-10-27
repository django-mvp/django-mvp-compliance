# Implementation Plan: Comparing two versions of a document

**Branch**: `014-comparing-versions` | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

## Summary

A page at `<slug>/compare/?from=<number>&to=<number>` shows two published versions of one document
as one text, with the words added and removed marked, built from each version's stored HTML by a
small `Comparison` class on the standard library's `difflib`. Links to it are added to the
document's page, the account area's list and the page asking to agree. On the staff page that
produces everything held about a person, each acceptance's version links to the version's admin
page. The approved sketch's templates, copy and stylesheet are kept. The code behind them is
rebuilt test-first.

## Technical context

Python 3.12+, Django 5.2 to 6.1. No new dependency and no migration. Tests with pytest and
pytest-django, settings `tests.settings`. Performance target: a comparison of two texts of about
15,000 words answers within one second (SC-004).

## Constitution check

- **Article I, testing**: every behaviour starts from a failing test. Wording and appearance are
  not tested. What is marked, which comparison is offered, and what answers "not found" are.
- **Articles II, III and VII**: one class, one view, one stylesheet, no new dependency (D9).
- **Article V**: the output is built only from stored, sanitised HTML plus the marks, and the one
  translated label inside a mark is escaped. A test proves the output holds no tag the two inputs
  do not.
- **Article VIII**: every new string is in the English catalogue, and the page-strings test lists
  the new template.
- **Article X**: the comparison is a class, `Comparison`, with the splitting and marking as its
  methods. A host project can subclass it.
- **Article XI**: nothing is written. Versions and acceptances are only read.
- **Article XII**: the stored HTML is compared and Markdown is never rendered.
- **Article XIII**: no string claims compliance or names a regulation.
- **Article XIV**: no personal data is added. `AcceptanceEntry.version_id` is the version's key,
  not data about a person.
- **Article XV**: `AcceptanceEntry` gains a field, recorded in the CHANGELOG.

## Design

### `mvp_compliance/comparison.py`

```python
class Comparison:
    older: Version
    newer: Version
    similarity = 0.5          # how alike two elements must be to be compared word by word
    window = 8                # how many unpaired older elements a newer one is tried against

    @classmethod
    def of(cls, first, second) -> "Comparison"   # orders by published_at (FR-008)
    @property
    def same(self) -> bool                       # identical ignoring whitespace (FR-010)
    def html(self) -> SafeString                 # the marked text (FR-002 to FR-006)
```

Splitting into top-level elements, opening lists into items, pairing, word marking and the
whitespace folding are methods of the class, as in the sketch. Pairing tries each newer element
only against the next `window` unpaired older elements, which bounds the pass at elements × window
(research, "Pathological input").

- **Tags are matched quote-aware**: `<(?:[^>"']|"[^"]*"|'[^']*')*>`, so a `>` inside an attribute
  value never ends a tag, whatever the sanitiser's serialisation.
- **The newer version's wrappers are the only wrappers.** A removed element that carries no words
  (a bare list wrapper) emits no tags. A wholly removed list keeps its wrapper with its items inside.
  Every element in the output closes in order.
- **`same` compares words, tags removed** (D16): two versions differing only in markup, such as a
  link's address, are "the same", because `html()` would mark nothing between them.

### `ComparisonView`

An `MVPDetailView` on `Document.objects.in_force()` at `<slug:slug>/compare/`, before the document
route. One query reads the document's published versions with their replacement dates. `from` and
`to` must both name one of them, or the answer is 404 (FR-011). A document with one published
version answers 404 for any pair, never a redirect. The context holds the comparison,
the versions for the pickers and the documents for the side list, as the sketch has it.

### The links

- **Document's page**: the dropdown is drawn when the document has more than one published
  version. The replaced-version alert's comparison button uses the version in force, the newest of
  the versions the page already reads. The sketch's extra query for it is deleted.
- **Account area**: `get_entries` sets `since`, the first (newest) acceptance's version, on entries
  with a newer version in force.
- **Page asking to agree**: `get_entries` reads the person's acceptances of the listed documents
  once, newest version first, and sets `since` on each entry. The row component takes `since` as
  a prop, beside the summaries' `changes`.
- **Staff page**: `AcceptanceEntry.version_id`. The partial links the version text to
  `admin:mvp_compliance_version_change` when `perms.mvp_compliance.view_version`.

## Project structure

```text
mvp_compliance/comparison.py                           new
mvp_compliance/views.py                                ComparisonView; since on two pages
mvp_compliance/urls.py                                 the comparison route
mvp_compliance/records.py                              AcceptanceEntry.version_id
mvp_compliance/admin.py                                the sketch's wrapper removed
mvp_compliance/static/mvp_compliance/comparison.css    kept from the sketch
mvp_compliance/templates/...                           kept from the sketch, plus the staff partial
mvp_compliance/locale/en/LC_MESSAGES/django.po         new strings
tests/test_comparison.py                               new
tests/test_views.py, tests/test_records.py, tests/test_admin.py
docs/pages.md, docs/disclosure.md, README.md, CHANGELOG.md
specs/004, 006, 008, 009 spec.md                       brought up to date
```

## Complexity tracking

| Addition | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| A tokeniser over HTML (a regular expression) | The comparison must keep the text's structure and mark words inside it | Comparing text with the tags stripped loses headings, lists and links (FR-004) |
| A package stylesheet | `<ins>` and `<del>` need a look that does not rely on colour | The prebuilt stylesheet has no rule for them and no colour-with-opacity utility |
