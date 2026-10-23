# Decisions — FS-012

Ambiguities resolved while the spec was written, with the reasons. The short form of each is in
the spec's Clarifications.

## D1 — The page needs a declaration to exist

A project that installs the package and mounts its pages, but has said nothing about its own data,
gets no page. Without a declaration, the only thing a copy could hold is the person's acceptances,
and a download offered as "a copy of your data" that holds only those reads as everything the site
holds. Making the page depend on the declaration turns the decision into the project's, which is
where Article XIII puts it. An empty declaration is allowed, so a project that really does hold
nothing else about a person can still offer the page.

## D2 — ADR 0012 stays for the staff page and is superseded for the person's copy

ADR 0012 forbade anything outside the package from adding to the answer about a person, because a
project that implemented an extension badly would produce an answer that looked complete and was
not. The person's copy cannot avoid that risk: reaching a project's data through a hook the
project implements is what R11 and Article XIII ask for. The risk is handled instead by refusing to
hand over a copy if any part of it fails (US-1), and by naming every kind the copy holds without
claiming it is everything (US-1). The staff page keeps ADR 0012 unchanged. A new ADR records the
split.

## D3 — The copy carries the time it was made

ADR 0013 keeps the staff answer free of a production time so that two readings of the same records
are equal. A person's copy is not evidence handed to somebody else. It is the person's own file, and
somebody who downloads two copies needs to know which is newer. The package's own section inside
the copy still carries only the times stored on the acceptances.

## D4 — No limit on how often a person can ask

Each request builds a copy afresh and keeps nothing. A limit would need the package to store when a
person last asked, which is personal data it otherwise has no reason to keep, and a project that
needs one has throttling of its own. Moving the work off the web request is #116.

## D5 — The page requires django-allauth to confirm identity

The sketch review asked for confirmation as a separate step, the way allauth guards its sensitive
pages. allauth's `reauthentication_required` does exactly that, and a page of the package's own
would be a second password form without allauth's rate limits, second factors or memory of when
a person last confirmed. allauth becomes an optional extra, and a system check reports a declared
copy on a site without it. Detail in research.md, "Confirming identity".

## D6 — Opening the page asks, not pressing the button

allauth's decorator can let the page be viewed and ask only on the download. It then replays the
download after confirmation, which leaves the person on the confirmation page while the file
arrives. Guarding the whole page makes confirmation the first step and returns them to the page,
which is what allauth's own sensitive pages do. A download pressed after the confirmation has
expired is still replayed from the confirmation page by allauth, which is acceptable.

**ADR:** none — the page's flow, recorded in docs/how-to/declare-what-the-project-holds-about-a-person.md.

## D7 — A kind that is always one record says so

The design review offered to drop `single` and lay out any kind with one row as label and value
pairs. Kept: the approved screen shows a profile as pairs because a profile is always one record,
and a list of datasets that happens to hold one should still read as a table.

**ADR:** none — local to how the copy is laid out.

## D8 — The how-to page lives under docs/how-to/

**Decision:** the page that tasks.md names `docs/personal-data.md` is
`docs/how-to/declare-what-the-project-holds-about-a-person.md`.

**Why:** the conformance check refuses a new page outside `tutorial`, `how-to/`, `reference/` and
`explanation/`, and the page is a how-to. The older flat pages are not new, so they pass.

**Revisit if:** the flat pages are moved, or US-1 adds a reference page for the settings.

## D9 — The stub page view is removed until T008

**Decision:** `PersonalDataView` and the `data/` route were removed after T001 rather than kept as a
stub. The three templates and the menu entry stay; the menu drops the entry while no route exists.

**Why:** the docs gate counts a new public view that no page documents, and the stub answered on
every project whether or not it declared anything, which Article XV forbids. T008 builds the view
and the conditional route.

**Revisit if:** T008 is dropped from the plan.

## D10 — django-allauth is exempt from deptry's unused-dependency rule

**Decision:** `django-allauth` is listed in deptry's `DEP002` ignore, as `django-mvp` is.

**Why:** the extra is declared in this story, and no package module imports allauth until T008. The
system check names allauth's app and middleware as strings.

**Revisit if:** T008's guarded import makes the ignore unnecessary, in which case remove it.

## D11 — An account with nothing to confirm with is not asked

**Decision:** an account with no password and no second factor reaches the page and downloads its
copy without being asked to confirm, because allauth treats it as recently confirmed. The package
adds no stricter rule of its own. The spec's FR-010, SC-004 and the assumption about confirming
are amended to say so.

**Why:** Sam's ruling, 2026-10-23, after the design review (SEC-001) found that allauth's
`did_recently_authenticate` returns true for such an account
(`allauth/account/internal/flows/reauthentication.py:76-83`). It matches allauth's own sensitive
pages, such as adding a second factor, and does not lock a person out of their own data.

**ADR:** none — follows allauth, recorded in the spec and the how-to page.

## D12 — A section records the kind that produced it

**Decision:** `PersonalDataSection` has a `kind` field, the dotted path of the declared kind, filled in by `PersonalDataCopy.collect`. The copy uses it to name the kind when a file cannot be opened or the kind's own template raises while the copy is written.

**Why:** the plan names the kind's path in every failure, but a section alone does not say which kind made it. Carrying the path with the section avoids a second mapping beside it.

**Revisit if:** sections are built anywhere other than `collect`, in which case the field is empty and the failure names no kind.

## D13 — US-3 was built directly, not dispatched

**Decision:** the two tasks of US-3, the signal and its three tests, were written by the
orchestrator rather than dispatched to an implementer.

**Why:** one signal declaration and one `send_robust` call in a view that already exists, with no
design content. A dispatch would have cost more than the work.

**ADR:** none — how the work was done, not a decision about the package.
