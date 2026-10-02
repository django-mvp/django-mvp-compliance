# Research — 008 What a person has agreed to, in their account area

The evidence behind the choices in [plan.md](./plan.md). Citations are to the packages the project
resolves in `.venv` (Django 6.1.1, django-mvp 0.25.0, django-flex-menus 0.4.6) and to this
repository at `origin/main` `33eb41a`.

There are no planning notes for this feature. The inputs are the specification and
[sketch.md](./sketch.md).

## What the prototype left to find a way to meet

### The address, and a slug that could take it

The package's URLconf has one route, `<slug:slug>/` (`mvp_compliance/urls.py`). A fixed route listed
ahead of it wins, so `agreed/` placed first never answers with a document. That settles the second
half of FR-014 by itself.

The first half, refusing the slug, has an existing seam: `Document.slug` carries the field validator
`lowercase_slug` (`models.py:37`, `models.py:145`), which the admin's form runs. A second validator
on the same field refuses a reserved slug in the same place and with the same mechanics. A field's
validators are part of its deconstruction, so this needs a schema-only migration that changes no
column.

A document already published under the slug `agreed` before the upgrade would stop being reachable,
and its slug is frozen (`Document.save()`, `models.py:175`). No route in the package can repair
that, so the CHANGELOG has to say it.

### A project without the account area

django-mvp's account area is mounted by including `mvp.urls`, and its landing page is the
un-namespaced name `account-center` (`mvp/views/account.py:52`, django-mvp
`docs/account-center.md`). There is no setting. Whether the area is mounted is therefore the
question "does `account-center` reverse".

- The menu entry: `AccountCenterMenu` (`mvp/menus.py:174`) is a module-level menu that always
  exists, so appending to it is safe in any project. An entry whose `view_name` does not reverse is
  made invisible when the menu is processed (`flex_menu/menu.py:397-404`), and its parent keeps
  only visible children. So in a project that does not mount
  the package's pages the entry disappears with no code of ours.
- The page: in a project that mounts the package's pages and not the area, nothing would draw the
  menu, but the address would still answer and its trail would fail to reverse `account-center`.
  FR-013 wants the page absent. The view has to answer "not found" itself.

### How the page comes to sit inside the account area

A page served from another app's URLs is treated as part of the area when `AccountCenterMenu` marks
it current: `MountedApp.claiming_menu()` (`mvp/mounted.py:286`) returns the first mounted app whose
processed menu has a selected item. A menu item declared with a `view_name` is selected by the request's resolved view name
(`flex_menu/menu.py:618-621`).
The prototype confirmed it on the running page: the sidebar swapped to the area's menu and the entry
was marked current. The layout is `mvp/account/base.html`, whose `account.content` block the page
fills.

### The queries

Two queries build the page whatever its length:

1. the person's acceptances of documents people agree to, joined to version and document
   (`Acceptance.objects.for_person(user)`, `models.py:814`, narrowed by `Document.Kind.AGREED`);
2. the versions in force of the documents found (`Version.objects.current()`).

`Document.objects.outstanding_for()` (`models.py:76`) answers a wider question, every document
including those never accepted, and returns documents and not versions. The page needs the version
in force's number and date for its statement, so it is not reused.

### What the existing tests say about menus

`tests/test_views.py::TestNoMenuEntry` guards FS-006's FR-014, "the package MUST NOT add anything to
the host project's menus or navigation". Its second test refuses any mention of `flex_menu` in the
package. FS-008's FR-011 requires an entry in the account area's menu, which is django-mvp's and
exists to be added to. The two requirements do not conflict. The test is wider than the requirement
it guards and has to be narrowed to what FS-006 asked for: the project's own menu, `AppMenu`, is
never touched.

`TestPageStrings` lists the page templates by name and checks every string against the `en`
catalog. Both follow the new templates.

## What the page needs, and where each comes from

| Need (sketch.md) | Met by |
|---|---|
| Every acceptance of a document people agree to, with number, status, name, slug, date | query 1 |
| Grouped by document, documents by name, versions newest published first | ordering on query 1, grouped in the view |
| The version in force and whether it was accepted | query 2 compared with query 1 |
| A fixed number of queries | two, asserted with one acceptance and with fifty |
| An address no slug can take | fixed route first, plus the slug validator |
| A menu entry only when both are mounted | the menu drops an unresolvable entry; the view answers "not found" without the area |
| Sign-in redirect | `LoginRequiredMixin` |
| The few shown first and the rest folded (FR-019) | split in the view |

## No new dependency

Everything used is already required: Django, django-mvp and the menu library django-mvp depends on.
`flex_menu` is imported directly for `MenuItem`, as django-mvp's own documentation shows, so it
becomes a direct dependency in `pyproject.toml` to keep `deptry` clean.
