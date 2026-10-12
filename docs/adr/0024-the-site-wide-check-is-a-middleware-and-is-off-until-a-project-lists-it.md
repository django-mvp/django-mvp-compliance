# ADR 0024 — The site-wide check is a middleware, and is off until a project lists it

**Status:** accepted

## Decision

Sending people to the page that asks is done by `mvp_compliance.middleware.AgreementMiddleware`,
and by nothing else in the package. A project switches the check on by listing it in `MIDDLEWARE`
after `AuthenticationMiddleware`. Without it the package redirects nobody, so installing or
upgrading changes no request.

The check only ever concerns a signed-in user. A visitor who is not signed in passes untouched,
and requiring a sign-in stays the project's own decision.

A project keeps addresses reachable with a list in its settings. There is no decorator for single
views. Three system checks report a configuration that cannot work: the page that asks has no
address, nothing that identifies the signed-in user comes before the middleware, or a list setting
was given as a string. At run time a check that cannot work lets every request through.

## Why

Marking up views one at a time is not dependable, because the view somebody forgets is exactly
where a person who has not agreed gets through. A middleware sees every request, including the
ones to views the project does not own.

It is opt-in because a package that started redirecting every signed-in user on upgrade would be
a breaking change no changelog entry could make safe. Adding one line is a deliberate act.

A list of addresses covers views in third-party packages, such as a payment callback, which a
decorator cannot reach. One mechanism is enough.

A misconfigured check is reported at start-up and passes requests through at run time because the
alternatives are a redirect to nowhere for every user, or a redirect loop. Both are found in
production.

## Revisit if

Projects ask to keep a single view of their own reachable without knowing its address. A decorator
in the manner of Django's `login_not_required` is the obvious addition, beside the list and not
in place of it.
