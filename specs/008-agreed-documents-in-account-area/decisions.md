# Decisions — 008 What a person has agreed to, in their account area

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible. The rulings made while specifying are in `spec.md` under *Clarifications*, and what was
settled by eye on the prototype is in `sketch.md`.

## D1 — The document page's layout changes with this feature

**Ambiguous**: the specification said this feature changes nothing on the document page and left
its design to issue #71. Review of the prototype asked for that page's list of documents to move
into a card in a column of its own, pinned while the document scrolls.

**Chosen**: the layout change ships here. `spec.md` is marked refined, with the scope sentence
struck through and the reason given. No user story was added.

**Why defensible**: the change was asked for by the person who approved the specification, on this
pull request. It alters layout only: what the page shows, who reads it and its addresses are
untouched, and its existing tests pass unchanged. The testing standard gives layout no acceptance
criterion, so there is nothing for a story to carry. The rest of #71 stays open.

**Revisit if**: #71 settles a different layout for the page.

**ADR:** none — a scope ruling for this feature; nothing later inherits it.

## D2 — The FS-006 menu test is narrowed, not removed

**Ambiguous**: `TestNoMenuEntry.test_the_package_does_not_touch_the_menu_library` refuses any
mention of the menu library in the package. FR-011 requires a menu entry in the account area.

**Chosen**: the test asserts that no module in the package names `AppMenu` or `MobileFooterMenu`, the
two menus django-mvp gives a project. Its sibling, which
checks the project's menu is unchanged after serving every page, stays as it is.

**Why defensible**: FS-006's FR-014 reads "the package MUST NOT add anything to the host project's
menus or navigation". The account area's menu belongs to django-mvp and exists for installed
packages to add to. The original assertion was wider than its requirement, and the narrowed one
still fails if the package ever touches the project's own menu.

**Revisit if**: a later feature wants an entry in the project's own menu, which FS-006 forbids.

**ADR:** docs/adr/0020-the-package-adds-to-the-account-areas-menu-and-to-none-of-the-projects.md

## D3 — The list's address is `agreed/`, and the slug is refused by a field validator

**Ambiguous**: FR-014 asks that no document may take the list's address, without naming the address
or where the refusal lives.

**Chosen**: `agreed/` beside the document pages, listed ahead of the slug route.
`Document.RESERVED_SLUGS` holds the segment, and a validator on `Document.slug` refuses it with the
code `reserved`.

**Why defensible**: a slug is already validated by a field validator, so the admin refuses a
reserved slug in the same place and the same way as an upper-case one. Route order alone guarantees
the address never answers with a document, including for a document created from code.

**Revisit if**: the package gains more fixed addresses beside the document pages. A prefix that no
slug can match would then be cheaper than a growing reserved set.

**ADR:** none — local to one field and one route; the reserved slug is documented in `docs/models.md`.

## D4 — A project without the account area gets "not found", decided by whether the area's address resolves

**Ambiguous**: FR-013 wants the page absent when the account area is not mounted. django-mvp has no
setting that says whether it is.

**Chosen**: the view answers 404 when the name `account-center` does not reverse.

**Why defensible**: mounting `mvp.urls` is the only switch django-mvp has for the area, and the
shell's own links to it are conditional on the same reverse. A URLconf cannot make the decision at
import time, because reversing while URLconfs are still loading is circular.

**Revisit if**: django-mvp publishes a way to ask whether the area is mounted.

**ADR:** docs/adr/0020-the-package-adds-to-the-account-areas-menu-and-to-none-of-the-projects.md

## D5 — Three versions shown before the fold

**Ambiguous**: FR-019 fixes three shown and a fold above four. Whether the number should be a
setting was open.

**Chosen**: a class attribute on the view, `shown_first = 3`. No setting.

**Why defensible**: the number was settled on the prototype. A project that wants another
subclasses the view and mounts its own route, which needs no new public setting to maintain.

**Revisit if**: a project asks for it.

**ADR:** none — one attribute on one view, documented in `docs/pages.md`.

## D6 — What the design review found, and what was done

One reviewer read the plan against the specification, the constitution and the resolved packages.
No finding against the specification, and none on security.

- **The string tests cannot read a plural (high).** The list's template holds the package's first
  `{% plural %}` block, and the two helpers behind the catalog tests would have reported it missing
  however the catalog was generated. T001 now teaches both helpers to read a plural. No assertion is
  loosened.
- **The catalog was regenerated a task too late (medium).** A task that adds a string now
  regenerates the catalog itself, so the suite is green at each task and not only at the story's
  last one.
- **Documentation still said the package adds nothing to menus (low).** T009 corrects those lines.
- **The narrowed menu test left the mobile dock unguarded (low).** It now names both of the
  project's menus (D2).
- **A test walking the URLconf for fixed routes was speculative (low).** Dropped. There is one fixed
  route, and both halves of FR-014 are tested without it (D3).
- **The admin case of the reserved slug sat in the models test module (low).** Moved to
  `tests/test_admin.py`.

Carried to the build as things to watch: the "not found" check comes before `super().dispatch()`
(T013), and a person with no acceptances costs one query fewer than a person with any, which
SC-005 does not compare.

`CONTEXT.md` lists *agreement* among the words to avoid for an acceptance. The menu entry's label,
"Agreements", was chosen in review of the prototype and is kept as approved wording. It is a label a
person reads, not a name in the code.

**ADR:** none — a record of review findings, not a decision that constrains later work.

## D7 — The groundwork was done directly, without a separate implementer

T001 and T002 remove code and edit two test helpers, the catalog and two documents. There is no
design in them and nothing to build, so they were done in place and checked with the full suite
before the first story was handed out.

**ADR:** none — how this run was carried out; nothing in the code depends on it.

## D8 — The projects that leave part out are tested with `pytest.mark.urls`

**Decision:** `TestWithoutTheAccountArea` and `TestWithoutThePackagePages` select their URLconf with
`@pytest.mark.urls("tests.urls_package_only")` and `@pytest.mark.urls("tests.urls_mvp_only")`, not
`@override_settings(ROOT_URLCONF=...)`.

**Why:** the suite's tests are plain classes, and Django refuses to decorate anything but a
`SimpleTestCase` subclass with `override_settings`. `tests/test_admin.py` already selects its URLconf
the same way. The marker also clears the URL caches around each test, so no resolver outlives it.

**Revisit if:** the suite moves to `TestCase` classes.

**ADR:** none — a test-suite detail that follows what `tests/test_admin.py` already does.
