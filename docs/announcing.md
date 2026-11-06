# Announcing a publication

When a version is published, this package sends a signal, `version_published`, so a host
project can act on it — email the owners, post to a channel, write its own audit trail —
without watching for it. The package sends nothing itself: no email, no message, no request.
It can write an email for you, to [the people running the site](#a-ready-made-email) or to
[the people who use it](#an-email-to-the-people-who-use-the-site), but rendering is not
sending, and what happens next is the host project's receiver.

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

## Every signal

All are in `mvp_compliance.signals`. Every argument is passed by keyword, and every signal is sent
only after the change has committed. A refused change, and a change inside a transaction that is
rolled back, sends nothing. A receiver that raises cannot undo the change, and the receivers after
it still run.

| Signal | Sender | Arguments | Sent |
|---|---|---|---|
| `version_pending` | `Version` | `version`, `by` | Once a draft is locked for translation. `by` is the account that locked it, or `None` |
| `version_returned_to_draft` | `Version` | `version`, `by` | Once a pending version is returned to a draft. `by` is the account that returned it, or `None` |
| `version_published` | `Version` | `version`, `publisher`, `replaced` | Once a draft or pending version is published, as described above |
| `translation_published` | `Translation` | `translation`, `publisher`, `replaced` | Once a translation is put live. `replaced` is the wording it superseded, already `Translation.Status.SUPERSEDED`, or `None` for a language's first. On a pending version readers are served the wording from the version's publication, which `version_published` announces; this signal is not sent again then |
| `translation_returned_to_draft` | `Translation` | `translation`, `by` | Once for each live translation a version's return to a draft sends back to a draft, before `version_returned_to_draft`. Translations that were already drafts are not announced |
| `personal_data_copied` | `PersonalDataView` | `user`, `kinds` | Each time a person's copy of their data is handed over. See [the how-to](how-to/declare-what-the-project-holds-about-a-person.md) |
| `account_deleted` | `DeleteAccountView` | `user`, `subject`, `kinds` | Once a person has deleted their own account. See [the how-to](how-to/delete-an-account.md) |

A receiver for a translation signal looks the same as one for `version_published`:

```python
from django.dispatch import receiver

from mvp_compliance.models import Translation
from mvp_compliance.signals import translation_published


@receiver(translation_published, sender=Translation)
def note_translation(sender, translation, publisher, replaced, **kwargs):
    ...
```

The admin passes the signed-in user as `by` and `publisher`. Called from code, each method takes
the account as an argument (`lock_for_translation(by=user)`, `return_to_draft(by=user)`,
`publish(publisher=user)`), and sends `None` when none is given.

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

## An email to the people who use the site

When a document the site's users agreed to changes, they often want to read the new wording
before they carry on. `render_new_version_email` writes that email: a subject, a plain-text body
and an HTML body. It sends nothing and chooses no recipient. Who hears about which document is
your decision.

```python
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver

from mvp_compliance.emails import render_new_version_email
from mvp_compliance.signals import version_published


@receiver(version_published)
def tell_the_users(sender, version, replaced, **kwargs):
    subject, text, html = render_new_version_email(version, replaced)
    message = EmailMultiAlternatives(subject, text, None, bcc=recipients_for(version))
    message.attach_alternative(html, "text/html")
    message.send()
```

`recipients_for` stands for your own choice of who is told, such as everyone who agreed to an
earlier version of the document. Send to them in `bcc`, or one message each, so nobody sees the
others' addresses. On a site with many users, have the receiver put the sending on a task queue,
as [Where it runs](#where-it-runs) says.

The email says:

- which document changed, and the date the new version applies from
- what changed, when the person who prepared the version wrote a summary, with its line breaks
  kept. With no summary the email has no part about what changed.
- a link to the document's page, and, when the version replaced another, a link to the page
  comparing the two

It never names who published the version.

### Where its links point

The HTML body extends django-mvp's email layout, `mvp/email/base.html`, so it carries your site's
name, logo and colours, and its links are full addresses. Both bodies take the address the way
that layout does, described in
[django-mvp's email documentation](https://github.com/django-mvp/django-mvp/blob/main/docs/developer/email.md#give-a-link-an-absolute-address):

- **With a request**, passed as `render_new_version_email(version, replaced, request=request)`,
  the links use that request's scheme and host.
- **Without one**, as in a signal receiver, they use the domain of the current `Site`. Install
  `django.contrib.sites`, set `SITE_ID` and give that `Site` your domain, or rendering raises
  `ImproperlyConfigured`.

The links point at the pages under `mvp_compliance.urls`, so the project must mount them.

### Changing its wording or its look

The email is three templates, and the text in each is translatable:

- `mvp_compliance/email/new_version_subject.txt`
- `mvp_compliance/email/new_version_message.txt`
- `mvp_compliance/email/new_version_message.html`

Put a template at the same path in one of your own template directories, ahead of the package's,
and yours is used. Each receives `version`, `replaced` (`None` for a first version),
`document_path` and `comparison_path` (`None` for a first version). The two paths are relative,
so turn them into full addresses with `{% email_url %}` after `{% load mvp_email %}`. Keep
`{% autoescape off %}` around the plain-text templates. To change how every email on the site
looks, replace django-mvp's layout rather than this template.

The subject is always a single line, whatever the document is called. The plain-text body carries
the document's name as written, and the HTML body escapes it.
