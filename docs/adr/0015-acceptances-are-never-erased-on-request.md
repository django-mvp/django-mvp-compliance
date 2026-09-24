# ADR 0015 — Acceptances are never erased on request

**Status:** accepted

## Decision

No path in this package deletes, blanks or selects among a person's acceptances because that person
asked. A request to delete a person's data reaches their account and whatever the host project
holds, and leaves their acceptances in place.

The one route that removes an acceptance stays the one ADR 0008 describes: removing the account,
when the project has set `MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL = False`.

## Why

An acceptance is the evidence of what a person agreed to. Its value is realised in a dispute, and a
dispute can arrive after the person has asked for their account to go. A package whose purpose is
keeping that evidence should not also offer the person it concerns a way to remove it.

The roadmap and the constitution previously promised an audited erasure path for acceptances. It
was never built. Keeping it would have meant a second deletion route beside the account-removal
setting, with its own permission and its own record of erasures, which is itself personal data
about the person who asked.

## Consequences

- A person's request to delete their data is handled at the account level, from pages this package
  places in the account area, with the deletion itself done by the host project's code (R11).
- A project that must remove acceptances when an account goes uses the setting from ADR 0008. The
  decision is the project's, made once in configuration, not per request.
