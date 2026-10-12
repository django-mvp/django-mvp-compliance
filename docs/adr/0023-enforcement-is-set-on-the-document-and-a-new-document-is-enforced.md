# ADR 0023 — Enforcement is set on the document, and a new document is enforced

**Status:** accepted

## Decision

`Document.enforced` says whether a document stops a person who has not accepted its current
version. It is `True` unless somebody chooses otherwise, and like the document's kind it is not
frozen by publication: it is changed at any time, from the admin or from code, and changing it
touches no version and no acceptance.

Enforcement narrows nothing about what a person has outstanding. `Document.objects.outstanding_for(user)`
still answers for every document people agree to
([ADR 0009](0009-outstanding-is-answered-for-every-published-document.md)).
`Document.objects.enforced_outstanding_for(user)` is that answer narrowed to enforced documents,
and it is the one question both the site-wide check and the page that asks act on.

## Why

A site that switches the check on has documents worth stopping people over, such as its terms, and
documents that are not, such as a cookie policy. Without a say per document the check would stop
every user over every document, and a project with a cookie policy could not switch it on.

The default is enforced because the check itself is off until a project lists the middleware, so
the default stops nobody on its own. A developer who then switches the check on expects it to do
something. A default of not enforced would leave a site looking protected while stopping nobody.

Keeping the two answers apart means a document that is not enforced is still listed as outstanding,
still offered on the page that asks, and its acceptance is still recorded like any other. A person
who never accepted the cookie policy shows up as such in the records, which is the truth.

## Revisit if

A document needs to be enforced for some people and not others. That is a rule about a person and
a document together, and one field on the document cannot hold it.
