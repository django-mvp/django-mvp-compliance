# ADR 0009 — "Outstanding" covers every published document, and carries no enforcement policy

**Status:** accepted

## Decision

`Document.objects.outstanding_for(user)` returns every document that has a version in force which
this person has not accepted. It does not filter by whether the site actually requires that document
to be accepted. A cookie policy that is published and never enforced appears in the answer.

`document.is_outstanding_for(user)` answers the same question about one document, and is that same
queryset narrowed to one primary key rather than a second expression of the rule.

## Why

Whether a document is enforced is a policy, and a policy compiled into the layer that holds evidence
is a policy that cannot be changed without touching evidence handling. The code that acts on the
answer — that decides somebody must accept something before continuing — is where enforcement
belongs, because that is the code the decision is about.

Filtering here would also be wrong for most of the callers. An account page showing somebody what
they have agreed to, and a site-wide view of who is outstanding on what, both want the unfiltered
answer. Only the code that blocks a request wants the filtered one, and it can filter. Building the
filter in would force two of the three consumers to work around it.

One rule with one implementation is the other half of this. Two implementations of "outstanding"
would drift, and the one that drifts is the one called on every page request. Narrowing the queryset
costs a `filter(pk=...)` and an `exists()`, both of which the database was going to do anyway, and it
means the query-count bound is proven once for both answers.

## Consequences

The cost of the answer is a correctness requirement, not a tuning exercise, because it runs on
ordinary page requests. It is one query with a subquery rather than a loop over documents, and a test
measures the query count across two documents and then across ten and asserts they are equal. That
test was checked against the failure it guards: an implementation that asks each document separately
fails it.

A document with nothing in force is never outstanding for anybody, because there is nothing to
accept. That is a normal answer rather than an error, as is an empty result for somebody who owes
nothing anywhere.

Accepting a version that is later superseded leaves that document outstanding again, because what is
in force is no longer what that person read. The earlier acceptance is untouched and still points at
the version it named.
