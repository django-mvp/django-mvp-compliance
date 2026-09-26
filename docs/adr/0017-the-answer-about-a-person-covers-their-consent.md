# ADR 0017 — The answer about a person covers their consent, not the work staff do

**Status:** accepted

## Decision

`mvp_compliance.records.produce()` and the admin's **Everything held about a person** page answer
what a person agreed to: their acceptances and, when cookie consent arrives, their cookie choices.
They do not list the versions a member of staff published, although each version records its
publisher (`Version.publisher`, `Version.publisher_subject`).

The statement of coverage the answer carries stays as it is.

## Why

The page exists so that someone fielding a request can show a person what they agreed to, and when.
Publishers are privileged staff acting in their role. Which versions they put in force is a record
of their work, kept so a version can say who approved it. It is not a record of their consent, and
nobody asking what they agreed to is helped by seeing it.

Adding it would make every answer longer and harder to read for every person, and cost a query and
a template to cover a case nobody raises. Read strictly, the statement of coverage leaves out the
publisher's account identifier. It is read as a statement about the person's consent, and on that
reading it is accurate.

## Revisit if

A project needs to answer a request from a member of staff about their own activity in the admin.
That is an audit question about staff, and it belongs to whatever the project uses to answer it,
not to this page.
