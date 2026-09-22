# ADR 0011 — Producing what is held is an admin page on a model with no table, behind its own permission

**Status:** accepted

## Decision

Everything this package holds about one person is produced at a single address in the Django admin,
`/admin/mvp_compliance/disclosure/`, and reaching it requires `mvp_compliance.produce_disclosure`,
which nobody holds until it is granted.

The page hangs off `Disclosure`, a proxy of `Acceptance` that adds no fields and creates no table. It
exists so the act has a name in the admin index, an address, and a permission of its own. Its admin
replaces the changelist outright and never calls Django's: there is no list of records, and nothing
about the named person is read until after the permission check. `Acceptance` itself is not
registered in the admin, and this package still serves no address outside it.

## Why

This is the one place the package assembles one person's consent history and hands it over, which
makes it the highest-value surface here by a distance. Everything else it offers is about documents.
Reusing the permission that governs writing a document would give every compliance editor the
ability to pull any member of the public's record, which is a different job with different risk, so
the act gets a permission nobody has by default — a permission that arrives switched on is one
nobody decided to grant.

A `ModelAdmin` needs a registered model, and the three real models are each the wrong home. The page
is about a person, not about a document or a version. Registering the acceptance record itself was
the obvious route and is the one thing to avoid: it would hand everyone holding an ordinary viewing
permission a browsable list of every person's consent history, which is precisely the exposure the
new permission exists to close.

A proxy model gets its own content type in Django, so the permissions declared on it are its own.
Holding any permission on the acceptance record grants nothing on the proxy, and the routine
add/change/delete/view permissions Django creates for the proxy grant nothing either, because every
hook on its admin consults only the new one. A test grants somebody all of them and confirms the
page still refuses.

The alternative was to ship a URL configuration for host projects to include. That would make this
the first address the package serves outside the admin, and it would leave every consuming project
responsible for mounting it behind something — a package that is only safe when the consumer
configures it correctly is a design problem, not a documentation one.

Refusals happen before anything about the named person is read, so a refusal for somebody with
records and a refusal for somebody without them are the same response. A surface that distinguished
the two would be a way of confirming that a given person uses the site.

## Revisit if

A host project needs to produce an answer somewhere other than the admin — an account page where a
person sees their own records is a different audience and cannot share this permission, and building
it may be the point at which the underlying function needs a second, differently gated caller.
