# Announcing a publication

When a version is published, this package sends one signal, `version_published`, so a host
project can act on it — email the owners, post to a channel, write its own audit trail —
without watching for it. The package sends nothing itself: no email, no message, no request.
It can write the text of an email for you, as described [below](#a-ready-made-email), but
rendering is not sending, and what happens next is the host project's receiver.

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

## A ready-made email

Most projects that listen for `version_published` send the same email to the people who run
the site. `render_publication_email` writes its subject and body from the signal's values and
returns them. It sends nothing, chooses no recipient and makes no request.

```python
from django.core.mail import send_mail
from django.dispatch import receiver

from mvp_compliance.emails import render_publication_email
from mvp_compliance.signals import version_published


@receiver(version_published)
def tell_the_site_owners(sender, version, replaced, **kwargs):
    subject, body = render_publication_email(version, replaced, site_url="https://example.com")
    send_mail(subject, body, None, ["owners@example.com"])
```

`site_url` is the address your site is served at. The package has no way to know it, so you
supply it, and the body carries it joined to the admin page for the version.

The body names the document, the version number, who published it and when, and either the
number of the version it replaced or that this is the document's first version in force. Who
published it is `version.publisher_display`, so a version published with nobody named, or by an
account since removed, says so.

**Send the body as plain text, never as `html_message`.** The names in it are not escaped, so a
document called `<b>Terms</b>` arrives as those characters. The subject is always a single
line, whatever the document is called.

### Changing the wording

The subject and body are two templates, and the text in both is translatable:

- `mvp_compliance/email/version_published_subject.txt`
- `mvp_compliance/email/version_published_body.txt`

Put a template at the same path in one of your own template directories, ahead of the
package's, and yours is used. Each receives `version`, `replaced` (`None` for a first version)
and `admin_url`. Keep `{% autoescape off %}` around the text, since it is not HTML. The
package's own strings are in English; the language is the one active when the function is called.
