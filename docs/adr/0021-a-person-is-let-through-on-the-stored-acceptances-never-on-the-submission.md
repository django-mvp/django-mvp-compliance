# ADR 0021 — A person is let through on the stored acceptances, never on the submission

**Status:** accepted

## Decision

The page that asks a person to agree decides whether to send them on by asking the database, after
its write, what is still outstanding for them. It does not decide from what the form carried, and
it does not decide from the write having raised no error.

A write that fails is caught, logged with its traceback on `mvp_compliance.views`, and answered
with the page again. The write sits inside a transaction, so a submission that fails part-way
leaves none of its acceptances behind.

Anything that later sends people to this page, or lets them past it, asks the same question the
same way: `Document.objects.outstanding_for(user)`.

## Why

The package exists so that a site can produce, later, the record of what a person agreed to. A
person who was let through with no acceptance behind them is the one failure it cannot afford, and
it would only be found when somebody asked for the evidence.

A decision taken from the submission is right whenever the write worked. A decision taken from the
absence of an exception is right whenever every failure raises. A decision taken from the stored
records is right in both cases and in the ones nobody thought of: a write replaced by a project's
own code, a database that accepted the statement and kept nothing, a version replaced in the
instant between the read and the write. In each of those the person stays on the page. The last
of them can still leave an acceptance of the version just replaced, which is a true record and
lets nobody through.

The second read costs two queries on a path a person takes a handful of times in the life of an
account.

## Revisit if

The check across a whole site needs to answer on every request and cannot afford the query. Its
answer would then be cached, and the cache would have to be cleared by the write, which brings back
the question of trusting the write.
