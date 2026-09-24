# Decisions — 005 Announcing that a version was published

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — A failing receiver never fails the publication

**Ambiguous**: Django's ordinary way of sending a signal lets a receiver's error propagate to
whoever sent it. The issue says nothing about what should happen when a project's receiver fails.

**Chosen**: every receiver runs, an error in one is logged, and the publication stands and is
reported as a success (FR-005, FR-006).

**Why defensible**: the signal is sent after the publication commits, so by the time a receiver
fails the version is already in force and nothing can take that back. Letting the error through
would show the person publishing an error page for something that succeeded, and the natural
response is to try again, which the package then refuses as already published. It would also let
one broken receiver stop every receiver connected after it. The cost is that a failure is quiet
unless the project watches its logs, which is where a project already looks for errors in its own
code.

## D2 — A removed publisher's account leaves a trace, not a name

**Ambiguous**: the issue asks for who published a version. It says nothing about what the record
says once that person's account is removed, and the two easy answers both have a problem.
Removing the version with the account is impossible, because a published version is permanent.
Clearing the link leaves the version looking exactly like one published from code with no person
behind it.

**Chosen**: the version keeps enough to say "published by an account since removed" and nothing
that names the person (FR-013, FR-014).

**Why defensible**: it is the choice the package already made for acceptances in ADR 0008 and
ADR 0014. A record that can no longer say whether a person stood behind a publication has lost the
fact it exists to hold. A name or an email address kept about somebody whose account was removed
is the host project's decision to make, not the package's. A project that keeps its own record of
who an account belonged to can still answer "who was it?" from the identifier left behind.

## D3 — The admin link needs a site address from the project

**Ambiguous**: the email links to the version in the admin, but a signal is sent without a request,
so the package cannot know the site's address.

**Chosen**: the project supplies the address when it renders the email (FR-018). How it supplies it
is left to planning.

**Why defensible**: the project is the only party that knows its public address, and it is already
writing the receiver that renders the email. Guessing the address from Django's sites framework
would add a dependency many projects do not install, and it is still wrong for a site served
under more than one address.

## D4 — Versions a person published are not yet part of what the package produces about them

**Ambiguous**: `records.produce()` answers "everything this package holds about a person" (FS-004
FR-001), and its statement of coverage says so. This feature makes the package hold one more thing
about a member of staff: the versions they published, through `publisher_subject`. This spec does
not ask for that to join the answer, and adding it moves the fixed query count FS-004 pins in its
tests from one to two.

**Chosen**: nothing about the answer changes in this plan. The gap is put to the maintainer, with
the recommendation that a *Versions published* section join the answer the way FS-004 FR-017
anticipated, before this feature merges.

**Why defensible**: adding a section changes what the page shows about a person, which is a
decision about personal data rather than an implementation detail, and it would change a test from
another feature. Leaving it silent would ship an answer whose statement of coverage is no longer
true.

**ADR:** pending — decided with the maintainer before the merge gate
