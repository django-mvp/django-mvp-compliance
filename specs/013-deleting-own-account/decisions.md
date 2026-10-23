# Decisions — FS-013

## D1 — The package removes the account, which Article XIII does not yet allow

Article XIII says code in this package never deletes data held in another application's models.
The account is a row of the project's user model, so removing it is exactly that. The alternative
was to leave removing the account to the project's own code and check afterwards that it is gone.
It was put to Sam with the reading of the issue, and he chose the package removing it: a page that
says an account has been deleted must not depend on each project remembering the last step.

The build amends Article XIII to name this one removal: the signed-in person's own account, at their
request, after every kind the project declares has run its own deletion. Everything else the
project holds is still reached only through the project's code. A new ADR records the amendment and
the reason.

## D2 — Deletion is switched on by the declarations, not by a setting of its own

A separate setting would let a site offer deletion while some declared kind had never said how it is
deleted, so the page would promise more than the deletion does. Tying the page to every declared
kind saying how it is deleted (FR-018, FR-019) makes the declarations the only switch, and leaves a
project that declared its kinds for the copy alone exactly as it was.

## D3 — Files outside the database are the kind's own responsibility

FR-011 promises that nothing in the database changes when a deletion fails. A file a kind's own code
has already removed from storage cannot be put back by rolling the database back. Research decides
whether the package can do better than documenting this, for instance by running the kinds that
only delete rows first. The spec promises no more than the database.
