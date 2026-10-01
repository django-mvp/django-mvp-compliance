# Progress — 008 What a person has agreed to, in their account area

The running log of this feature's implementation run. The ledger (`feature-state.json`) is the
machine record; this is the readable one.

---

## 2026-10-01 — Prototype

The specification was approved by review on #77. No feature had been delivered since it was
written, so there was nothing to re-read it against. A prototype of the page was built on this
branch and reviewed on the running demo. Review changed the menu entry's label, moved the document
page's list into a pinned card in its own column, and folded long histories. The prototype was
approved the same day. What it needs from the code and what it faked are in `sketch.md`.

## 2026-10-01 — Plan

Research, plan and tasks written against `origin/main` at `33eb41a`. The specification is marked
refined for the two changes that came out of the review (decisions.md D1, FR-019). Three stories,
run in sequence after a foundational step that removes the prototype's untested Python so it is
rebuilt behind failing tests. Every functional requirement and success criterion maps to at least
one task.

The suite on the prototype commit: 437 passed, 6 failed. All six are accounted for in the tasks:
the menu test narrowed in T007 (decisions.md D2), and five string and catalog tests fixed in T001.

## 2026-10-01 — Design review

One reviewer, three lenses. Verdict: changes requested, on one high finding about the test helpers
for translated strings, which could not read a plural. Six findings in all, none against the
specification and none on security. All six were applied as edits to the plan and tasks
(decisions.md D6). Each premise the plan rests on about django-mvp and its menu library was checked
against the installed packages and holds.

## 2026-10-01 — Plan passed; groundwork

The plan was passed as written. T001: the prototype's view, route and menu entry are removed, the
demo's link to the list with them. The two helpers behind the string tests read plural entries, and
the `en` catalog is regenerated for the three page templates: fourteen strings added, none removed
or changed. T002: `docs/pages.md` and the changelog describe the document page's new layout and the
custom property for the card's offset. Full suite: 443 passed.

## 2026-10-01T21:30:00Z · Implementer US1 · T003

Did: `tests/test_models.py::TestAcceptancesOfAgreedDocuments`, five tests (six cases): own records of documents people agree to only, ordering by document name then newest published first, a version never accepted between two accepted ones is absent, a document made a notice drops out and returns (`save` and `update` routes), one query with version and document loaded.
Verified: `uv run pytest tests/test_models.py::TestAcceptancesOfAgreedDocuments -q` gives 6 failed, all `AttributeError: 'AcceptanceQuerySet' object has no attribute 'of_agreed_documents'`.
Next: T004 adds the method and the manager forwarder.
Watch: none.
