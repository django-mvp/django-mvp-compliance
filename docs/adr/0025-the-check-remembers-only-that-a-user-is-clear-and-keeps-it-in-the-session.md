# ADR 0025 — The check remembers only that a user is clear, and keeps it in the session

**Status:** accepted

## Decision

When the site-wide check finds that no enforced document is outstanding for a user, it stores the
time of that finding in the user's session and does not ask the database again until
`MVP_COMPLIANCE_AGREEMENT_CHECK_INTERVAL` seconds have passed, sixty by default. With `0` nothing
is stored and every request is checked.

Nothing else is ever remembered. A user who is being stopped is asked about on every request. So
is an account let past by the `mvp_compliance.skip_agreement` permission, and that permission is
read only for a user who would otherwise be stopped. An account named in
`MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS` is let past without a query.

## Why

Nearly everybody on a site has nothing outstanding, and a query on every one of their requests is
the cost the check must not have. The alternative to a delay is a store shared by every process
and cleared on publication, which a package cannot assume a project runs.

Remembering only the clear finding keeps the two guarantees that matter. Somebody who has just
agreed is let through on the next request, because they were never remembered as stopped. Somebody
whose acceptance failed is never let through, because being let through is always read from the
stored acceptances
([ADR 0021](0021-a-person-is-let-through-on-the-stored-acceptances-never-on-the-submission.md)).
What the delay costs is that a newly published version starts stopping people up to a minute late.

The session is used because the specification assumes Django's sessions, the session is loaded
anyway to tell a signed-in user from a visitor, and signing in as somebody else or signing out
flushes it, so a finding never passes between accounts. The cache framework's default backend is
per-process, which would make the delay depend on which worker answers.

The time the finding was made is stored, not the time it expires, so a project that shortens the
delay is not held to findings stored under the longer one.

Not remembering the permission means taking it away takes effect on the next request. The price
is paid only by a holder who has an enforced document outstanding, and only until they accept it.

## Revisit if

A site lets a large group past by the permission and never has them accept, so that the permission
is read on every one of their requests. Or a project runs without sessions.
