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

**ADR:** none — the page's flow, recorded in docs/personal-data.md.

## D7 — A kind that is always one record says so

The design review offered to drop `single` and lay out any kind with one row as label and value
pairs. Kept: the approved screen shows a profile as pairs because a profile is always one record,
and a list of datasets that happens to hold one should still read as a table.

**ADR:** none — local to how the copy is laid out.
