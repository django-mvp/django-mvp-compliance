# Announcing a publication

When a version is published, this package sends one signal, `version_published`, so a host
project can act on it — email the owners, post to a channel, write its own audit trail —
without watching for it. The package sends nothing else itself: no email, no message, no
request. What happens next is the host project's receiver.

```python
from django.dispatch import receiver

from mvp_compliance.models import Version
from mvp_compliance.signals import version_published


@receiver(version_published, sender=Version)
def note_publication(sender, version, publisher, replaced, **kwargs):
    ...
```

Connect the receiver somewhere that runs at startup, such as an `AppConfig.ready()`.

## When it is sent

Once for each successful call to `Version.publish()`, whether it came from the admin's publish
page or from your own code, and only after the publication has committed.

- **Nothing is sent for a refusal.** A version that is already published, a draft whose output
  is empty once whitespace is stripped, and a draft that says exactly what the version in force
  already says each raise `PublishError` and announce nothing.
- **Nothing is sent for a publication that is rolled back.** If `publish()` runs inside a
  `transaction.atomic()` block that later raises, the publication is undone and so is the
  announcement. When the outermost transaction commits, the receiver runs, and a query it makes
  sees the new version as current.
- **Called outside a transaction,** `publish()` commits as it returns and the receivers have
  run by then.
- **Two documents published in one transaction** are each announced once, after it commits, in
  the order they were published.
- **A receiver that publishes another version** announces that one too.

## What it carries

The sender is the `Version` class. Every argument is passed by keyword.

| Argument | Value |
|---|---|
| `version` | The version now in force, with its `status`, `published_at`, `html` and `publisher` set. |
| `publisher` | The account that published it, or `None` when `publish()` was called without one. |
| `replaced` | The version this one superseded, with its `status` already `Version.Status.SUPERSEDED`, or `None` for a document's first publication. |

Accept `**kwargs` as well, so a receiver keeps working if an argument is added later.

## When a receiver fails

A receiver that raises cannot undo or hide the publication. The version stays current, the
caller's `publish()` returns normally, and the admin still redirects with its success message.
The signal is sent with `send_robust`, so the remaining receivers still run.

The failure is logged, with its traceback, on the `django.dispatch` logger at `ERROR`. Django's
default logging configuration shows that only when `DEBUG` is on or `ADMINS` is set, so a project
that relies on a receiver should route that logger to somewhere it will be seen:

```python
LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django.dispatch": {"handlers": ["console"], "level": "ERROR"}},
}
```

## Where it runs

Receivers run synchronously, in the request that published, after the commit. A slow receiver
makes that request slow, so put slow work, such as sending mail through an external service,
on a task queue and have the receiver only enqueue it.

## Testing a receiver

The signal is sent from a commit callback, so a test only sees it once callbacks run. With
pytest-django, wrap the publication in `django_capture_on_commit_callbacks(execute=True)`; in a
Django `TestCase`, use `self.captureOnCommitCallbacks(execute=True)`. Disconnect any receiver
the test connected when it finishes.
