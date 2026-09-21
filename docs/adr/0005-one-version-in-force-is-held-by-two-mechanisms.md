# ADR 0005 — Two mechanisms hold "one version in force", and which one carries depends on the backend

**Status:** accepted

## Decision

Both of these ship, and both are load-bearing:

- A unique constraint on `Version`, conditional on the row being current, named `one_current_version_per_document`.
- A `select_for_update()` row lock on the document, taken inside `publish()`'s transaction before anything moves.

What each gives you depends on the database underneath:

| Backend | Conditional unique constraint | Row lock |
|---|---|---|
| SQLite | enforced | ignored, and not needed — writers already serialise |
| PostgreSQL | enforced | real |
| MySQL and MariaDB | **not created at all** | real, and the only thing holding the rule |

## Why

MySQL and MariaDB support neither partial indexes nor a filtered unique constraint. Django does not refuse the model. It raises system check `models.W036` and leaves the constraint out. A project on MySQL therefore has the model it asked for and not the database guarantee it looks like it has.

Dropping the constraint so every backend behaves the same would give up a real guarantee on the two backends that can provide it and buy nothing. Keeping it and saying nothing would leave a MySQL project believing in something it does not have. So both mechanisms ship and the difference is written here.

A MySQL-backed project loses the backstop, not the behaviour. The lock serialises publication through `publish()`, which is the only route this package offers, so two simultaneous publishes still leave exactly one version in force. What it will not survive is a write reaching the table by another road, such as raw SQL or a bulk load. That is outside the package's reach on every backend. One backend simply has no net underneath it.

This package's tests run on SQLite, where the constraint is exercised. Nothing here has been verified against MySQL, which is why the promise is written down rather than implied by a passing suite.

## Revisit if

A project runs this on MySQL and needs the backstop. The answer is a trigger or a check at the application boundary, decided with that project's constraints in view — not removing the constraint that works elsewhere.
