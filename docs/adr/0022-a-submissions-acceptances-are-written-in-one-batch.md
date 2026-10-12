# ADR 0022 — A submission's acceptances are written in one batch

**Status:** accepted

## Decision

`Acceptance.objects.record_many()` records one person's acceptance of several versions in a single
write, beside `record()`, which records one. It builds the rows and hands them to the queryset's
own `bulk_create` with `ignore_conflicts`, so the cost does not grow with the number of versions.

It keeps what `record()` guarantees. A version that was never published is refused before anything
is written. A notice's version is refused by the queryset, and nothing in the batch is written. A
version the person already accepted is passed over by the unique constraint on person and version,
and its record is left exactly as it was.

It differs from `record()` in two ways a caller can meet. It sends no `pre_save` or `post_save`
signal. It needs a database that can ignore conflicts on insert, which rules out Oracle.

## Why

The page that asks a person to agree records every document they agreed to in one submission. The
specification asks that showing the page and processing a submission each cost the same number of
queries for one document as for ten. `record()` costs several queries for each version: two checks
that the version is not a notice's, a read and a write, inside a savepoint.

The model already had both halves of a cheaper answer. The queryset's `bulk_create` refuses a
notice in one query for the whole batch, because nothing else stops a bulk write from skipping the
check in `save()`. The unique constraint over person and version is what makes a repeated
acceptance leave one record, and with `ignore_conflicts` the database applies it without a read
first.

Changing `record()` to go through the same write was considered and left alone. It returns the
acceptance, new or existing, which `ignore_conflicts` cannot give back, and code outside the
package may rely on its signals.

## Revisit if

An acceptance ever needs something a bulk write skips, such as a `save()` hook or a signal the
package itself listens for, or a project needs the page on Oracle.
