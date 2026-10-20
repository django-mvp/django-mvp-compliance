# Research — 011 Declaring the documents a site links to

Written against main at `4e241d2`. There is no `planning-notes.md` and no sketch.

## Prior art

How other Django code handles code that refers to a row which may not exist yet, read from each
project's source:

| Package | Where the declaration lives | A missing row when referenced | When rows are created |
|---|---|---|---|
| Django permissions | `Meta.permissions` | not applicable | `post_migrate`, missing rows only, never updated or deleted (`django/contrib/auth/management/__init__.py`, `create_permissions`) |
| Django sites | the framework | not applicable | `post_migrate`, only when the table is empty (`django/contrib/sites/management.py`, `create_default_site`) |
| django-dynamic-preferences | a class in an autodiscovered registry | created with the default | on read, or the `checkpreferences` command |
| django-constance | settings | the default, written on read | on read |
| Wagtail settings | a model class | created | on read |
| django-legaltext | a field naming the slug | created with an empty version | on read |
| django CMS `page_url` | a template id | empty, or raises when `DEBUG` is on | never |

The feature follows the first two rows: created after migrating, missing rows only. Creating on
read is rejected in `decisions.md` D2.

## How a declared document is created

A `post_migrate` receiver connected in `MvpComplianceConfig.ready()` with `sender=self`, so it runs
once per `migrate`, after every migration, on test database creation and after each `flush`. It
follows `create_default_site`:

- the `using` and `apps` arguments it is given, the historical `Document` from
  `apps.get_model("mvp_compliance", "Document")`, returning when the model is absent (a `migrate`
  back to zero) and when `router.allow_migrate_model(using, Document)` says no;
- the module is `mvp_compliance/management.py`, as `django.contrib.sites` names its own.

The historical model has the field defaults, so `kind` and `enforced` start as they do for a
document made in the admin (FR-003) without the receiver naming either.

## Checking a declaration before anything is written

Every missing declaration is checked first and nothing is written unless all pass (FR-008):

- slug and name: `Document._meta.get_field("slug").clean(value, None)` and the same for `name`,
  which run `lowercase_slug`, `unreserved_slug`, the length limits and the blank check the admin
  already runs;
- a name that belongs to another document under a different slug, read from the database, named
  in the message by that document's slug;
- two declarations that give the same name.

A failure raises `ImproperlyConfigured` with every fault listed, each naming its declaration. It is
Django's exception for a settings value that cannot work, and `migrate` stops with its message.
The creation runs in one `transaction.atomic(using=using)`.

## The slug lock

`Document.save()` and `DocumentQuerySet.update()` already refuse a slug change once a version is
published (ADR 0019). The same two places refuse it while the stored slug is declared, and the
admin's `get_readonly_fields()` adds `slug` for a declared document the way it does for a published
one. `get_prepopulated_fields()` already drops the prepopulation whenever the slug is read-only.

The refusal raises a new package exception, `DeclaredDocumentError`. ADR 0003 has every refusal
raise a package exception, and `PublishedVersionError` names a different breach.

Which slugs are declared is read from the setting at the point of use, never cached, as
`acceptances_survive_account_removal()` already does, so tests can override it.

## What already exists

```
the setting's reader               · 7, new     · searched models.py, checks.py; acceptances_survive_account_removal() is the pattern
creating rows after migrate        · 4, Django  · django.db.models.signals.post_migrate, as django.contrib.sites
slug and name validation           · 2, repo    · Document fields' clean(): lowercase_slug, unreserved_slug, max_length
the refusal to migrate             · 4, Django  · django.core.exceptions.ImproperlyConfigured
the slug lock in save() and update · 2, repo    · Document.save(), DocumentQuerySet.update() (ADR 0019)
the read-only slug in the admin    · 2, repo    · DocumentAdmin.get_readonly_fields(), get_prepopulated_fields()
the refusal's exception            · 7, new     · exceptions.py holds four, none for this breach
a template tag                     · 1, not needed · decisions.md D3
```

## The demo

`demo/settings.py` declares the three documents `demo/templates/demo/landing.html` links to.
`seed_demo` finds documents with `get_or_create(name=...)`, which finds a declared one, but its
`defaults` then never set the impressum's kind. The command sets the kind of a document it is about
to seed when it differs.

## The test settings

`tests/settings.py` declares nothing, so no test database gains a document it did not create.
Tests that need declarations override the setting and call the receiver, or run `migrate`.
