# ADR 0019 — A document's address is fixed once a version of it is published

**Status:** accepted

## Decision

A document's public address is built from `Document.slug`, never from its name. The slug is
lowercase letters, digits and single hyphens, and unique across documents. It can be changed
freely until a version of the document is published. After that, `Document.save()`, the queryset's
`update()` and `bulk_update()` refuse a change to it with `PublishedVersionError`. The name stays
editable in every state.

## Why

The address is what a footer links to and what a site has already sent to people, so it has to
outlive a rewording of the name. "Terms" becomes "Terms of use", and a privacy policy is renamed when
a second one appears for a different audience. An address derived from the name would break every
existing link at exactly that moment.

Fixing the slug when the document is created would be simpler to explain, but it would punish a typo
that nobody has seen yet. No address is served until something is published, so the slug is fixed at
the first publication, when the first link to it can exist.

The refusal lives in the model layer beside the rule that published versions are never written to,
and reuses the same exception, because both refuse a change to something already published. The
admin shows the slug read-only from that point, but it is not what enforces the rule.

## Revisit if

A site needs to move a published document to a new address. That would take a redirect from the old
address, not a writable slug.
