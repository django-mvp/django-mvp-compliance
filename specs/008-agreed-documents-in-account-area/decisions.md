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

## D2 — The FS-006 menu test is narrowed, not removed

**Ambiguous**: `TestNoMenuEntry.test_the_package_does_not_touch_the_menu_library` refuses any
mention of the menu library in the package. FR-011 requires a menu entry in the account area.

**Chosen**: the test asserts that no module in the package names `AppMenu`. Its sibling, which
checks the project's menu is unchanged after serving every page, stays as it is.

**Why defensible**: FS-006's FR-014 reads "the package MUST NOT add anything to the host project's
menus or navigation". The account area's menu belongs to django-mvp and exists for installed
packages to add to. The original assertion was wider than its requirement, and the narrowed one
still fails if the package ever touches the project's own menu.

**Revisit if**: a later feature wants an entry in the project's own menu, which FS-006 forbids.

## D3 — The list's address is `agreed/`, and the slug is refused by a field validator

**Ambiguous**: FR-014 asks that no document may take the list's address, without naming the address
or where the refusal lives.

**Chosen**: `agreed/` beside the document pages, listed ahead of the slug route.
`Document.RESERVED_SLUGS` holds the segment, and a validator on `Document.slug` refuses it with the
code `reserved`.

**Why defensible**: a slug is already validated by a field validator, so the admin refuses a
reserved slug in the same place and the same way as an upper-case one. Route order alone guarantees
the address never answers with a document, including for a document created from code. A test ties
the fixed routes to the reserved set.

**Revisit if**: the package gains more fixed addresses beside the document pages. A prefix that no
slug can match would then be cheaper than a growing reserved set.

## D4 — A project without the account area gets "not found", decided by whether the area's address resolves

**Ambiguous**: FR-013 wants the page absent when the account area is not mounted. django-mvp has no
setting that says whether it is.

**Chosen**: the view answers 404 when the name `account-center` does not reverse.

**Why defensible**: mounting `mvp.urls` is the only switch django-mvp has for the area, and the
shell's own links to it are conditional on the same reverse. A URLconf cannot make the decision at
import time, because reversing while URLconfs are still loading is circular.

**Revisit if**: django-mvp publishes a way to ask whether the area is mounted.

## D5 — Three versions shown before the fold

**Ambiguous**: FR-019 fixes three shown and a fold above four. Whether the number should be a
setting was open.

**Chosen**: a class attribute on the view, `fold_after = 3`. No setting.

**Why defensible**: the number was settled on the prototype. A project that wants another
subclasses the view and mounts its own route, which needs no new public setting to maintain.

**Revisit if**: a project asks for it.
