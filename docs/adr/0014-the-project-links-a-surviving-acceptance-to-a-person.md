# ADR 0014 — The project links a surviving acceptance to a person, not this package

**Status:** accepted

## Decision

A surviving acceptance holds the account's primary key and nothing else that identifies anybody. This
package will not hold an email address, a name, or a hash of either on a record whose account has been
removed.

A project that keeps acceptances past account removal is responsible for keeping its own record of
which person that identifier belonged to, in its own table, written when the account is closed.
`docs/models.md` says what to write and shows a `pre_delete` receiver that writes it. This package
ships no mechanism, no field and no setting for it.

## Why

The retention default only pays off if a surviving record can be found from what actually arrives in a
dispute, which is a name or an email address in a letter. `subject` is a primary key. Once the account
row is gone nothing in the database maps that number back to a person, so a record kept under the
default is neither usable evidence nor answerable to a request about the person it concerns. It is the
same property twice over: an orphaned identifier is safe to hold because nobody can link it to a human,
and worthless for the same reason.

There are two ways to close that gap. Hold something identifying on the record, or leave the link to
the project.

Holding it here means this package deciding, on behalf of every site that installs it, to retain
identifying data about somebody who asked for their account to be removed. What may be kept about that
person, and for how long, follows from a lawful basis and a retention policy that belong to the
project. A reusable package knows neither, so this is not its decision to make and not its data to
hold.

A configurable capture was considered and rejected: a JSON field filled by a project-supplied callable,
with a second callable supplying the lookup, since only whoever chose the contents can match against
them. It reaches the same outcome as the project keeping its own table, at the cost of an interface
this package would own and version forever, whose entire purpose is storing personal data it has just
concluded it should not store. Documentation reaches the outcome with no code, and puts the data where
the obligations governing it already apply.

Hashing an email address is not a way around the question. The Article 29 Working Party's opinion on
anonymisation techniques (05/2014) treats a hash as pseudonymisation rather than anonymisation, because
an email address is drawn from a small and guessable space and a hash of one is reversible by
dictionary attack. It remains personal data, and a project choosing it is making the same decision in a
different shape.

## Consequences

This package holds nothing identifying about a person whose account has been removed, under any
setting, and says so plainly in its documentation.

A project can turn retention on, write no map, and be left with records nothing can be matched to.
Nothing here can detect that, because the map lives somewhere this package cannot see. The
documentation carries the warning instead, and says that a project unwilling to keep the map should
turn retention off rather than hold data it cannot use.

The page that produces what is held needs no change. It already takes free text and falls through to
the stored identifier when no account matches, which is exactly what a project's own lookup hands it.

The default in [ADR 0008](0008-an-acceptance-outlives-the-account-it-names.md) is unchanged. This
decision says who is responsible for making a surviving record findable, not whether it survives.
