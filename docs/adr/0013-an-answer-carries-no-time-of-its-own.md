# ADR 0013 — An answer about a person carries no time of its own

**Status:** accepted

## Decision

Nothing in an answer is a clock reading. `produce()` reads no current time, no field on the answer
holds one, and the page that renders it carries no "produced at" stamp. Producing an answer twice
with no change to the records gives back an equal answer, which a test asserts by comparing two
productions directly and by confirming the current time is never read while one is built.

The moments an answer does carry are the ones stored on the records: when each acceptance happened.

## Why

An answer whose two readings differ cannot be evidence of anything, and an answer handed over in a
dispute is read by somebody looking for a reason to doubt it. A stamp saying when the page was
produced is the one thing that would make two readings differ while the records behind them are
identical, and it would do it for no gain, because whoever produced the answer already knows when
they did.

The frozen structures the answer is built from make this checkable rather than merely intended:
comparing two answers is an ordinary equality check, and it fails the moment anything variable
creeps in.

A site that needs to evidence how it responded to a request needs a record of the request and the
response it sent, which is a process it runs. Producing an answer is a read, and reads leave no
trace here — a log of who looked at whose data would be more personal data about people who did not
ask for it to be kept.

## Revisit if

An answer ever needs to be produced as a stored artefact rather than a page — a file kept as a
record of what was handed over on a given day would need the date, and the place to put it is the
record of the handover rather than the answer itself.
