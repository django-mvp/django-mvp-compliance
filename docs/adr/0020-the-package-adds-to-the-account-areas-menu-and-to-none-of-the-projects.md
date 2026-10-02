# ADR 0020 — The package adds to the account area's menu, and to none of the project's own

**Status:** accepted

## Decision

The package appends exactly one kind of thing to a menu: an entry in `AccountCenterMenu`, the menu
django-mvp draws inside its account area, for a page that belongs to the signed-in person. It never
names `AppMenu` or `MobileFooterMenu`, the sidebar and the mobile dock a project owns. Which of the
package's pages appear in a project's navigation stays the project's decision.

A page the package contributes to the account area answers "not found" when the project does not
mount the area, and its menu entry carries no check of its own: an entry whose address does not
resolve is dropped by the menu, so a project that does not mount the package's pages gets no entry.

## Why

The document pages are public and a project links to them from wherever it chooses, usually a
footer. Adding them to a project's sidebar would decide something the project had already decided,
which is why the pages feature ruled that the package adds nothing to a project's menus.

The account area is different. django-mvp ships it as a place for installed packages to add pages
about the person who is signed in, and a page with no entry in its menu is not drawn as part of
the area at all. The list of what a person agreed to is such a page, and without the entry a
person would have to know its address.

So the rule is about whose menu it is. The project's menus are the project's. The account area's
menu is django-mvp's, and it exists to be added to. A test holds the line by refusing any mention
of the project's two menus in the package.

Deciding whether the area is mounted by whether its address resolves is the same test django-mvp's
own shell uses for its links to the area. There is no setting to read.

## Revisit if

django-mvp gives a package a way to offer an entry that a project accepts or declines, or a project
asks for the document pages in its sidebar by default.
