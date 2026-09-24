# ADR 0016 — A publication is announced after it commits, and no receiver can undo it

**Status:** accepted

## Decision

`Version.publish()` announces a publication through the `version_published` signal. The send is
registered with `transaction.on_commit()` inside the block that publishes, after the last step that
can refuse. It is sent with `Signal.send_robust()`.

A receiver therefore runs only once the publication has committed, and never for a publication that
was refused or rolled back. A receiver that raises is logged by Django on the `django.dispatch`
logger. The remaining receivers still run, the version stays in force, and whoever published it is
told it was published.

The package connects no receiver of its own and sends nothing. What happens on a publication is the
host project's decision.

## Why

Telling people "the new terms are in force" about a version that was rolled back is worse than
saying nothing. Sending before the commit, or with a plain `send()` inside the transaction, would
risk exactly that. A receiver would also see a database that does not yet agree with what it was
told.

Once the commit has happened the version is in force, and nothing a receiver does can take that
back. Letting a receiver's error reach the caller would show the person publishing an error page
for something that succeeded, and the natural response, publishing again, is refused as already
published. It would also let one broken receiver stop every receiver after it. `send_robust()` is
Django's own mechanism for exactly this, so the package adds no error handling of its own.

The cost is that a failing receiver is quiet unless the project routes the `django.dispatch`
logger. With Django's default logging and `DEBUG` off, that error is only reported when `ADMINS`
is set. `docs/announcing.md` says so and shows the configuration.

## Revisit if

A project needs a publication and its side effects to succeed or fail together. That is a
transactional outbox or a task queue owned by the project, not a change to when this signal is
sent.
