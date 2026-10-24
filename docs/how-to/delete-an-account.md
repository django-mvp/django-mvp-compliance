# How to say how your project deletes what it holds about a person

A person can only have their account deleted if the package knows how to delete what your
project holds about them. You tell it by saying, on each [declared kind](declare-what-the-project-holds-about-a-person.md),
how that kind's records are deleted. Deletion is offered only when **every** declared kind says
how. While any kind is silent, nothing about deleting an account exists in your project.

## Before you start

Declare your kinds first, as in [How to declare what your project holds about a
person](declare-what-the-project-holds-about-a-person.md). The package's own section, the
documents a person agreed to, is not a kind you declare and is never part of this.

## Steps

1. For each kind, choose the way that fits what it holds.

   **The rows `get_queryset` returns are the whole of it.** Set `erasure` to `PersonalData.DELETE`
   and the package deletes exactly those rows, for that person and nobody else:

   ```python
   class Datasets(PersonalData):
       heading = _("Datasets you uploaded")
       model = Dataset
       fields = ["title", "licence", "created", "upload"]
       erasure = PersonalData.DELETE

       def get_queryset(self, user):
           return Dataset.objects.filter(owner=user)
   ```

   **Deleting the account already removes them.** A profile, or any model whose foreign key to the
   user is `on_delete=CASCADE`, goes with the account. Set `erasure` to `PersonalData.WITH_ACCOUNT`
   and nothing more is done for the kind:

   ```python
   class Profile(PersonalData):
       heading = _("Your profile")
       model = Profile
       fields = ["display_name", "bio"]
       erasure = PersonalData.WITH_ACCOUNT

       def get_queryset(self, user):
           return Profile.objects.filter(user=user)
   ```

   **Anything else is yours to do.** Override `erase(user)` and delete, cancel or anonymise what
   your project holds in whatever way is right for it:

   ```python
   class Subscriptions(PersonalData):
       heading = _("Your subscriptions")

       def collect(self, user):
           ...

       def erase(self, user):
           cancel_subscriptions(user)
   ```

2. If a kind has files, remove them after the deletion has committed. Deleting a row does not
   delete its stored file, and a file removed inside a transaction that then rolls back is gone
   for good while its row is still there. Collect the names first and hand the removal to
   `transaction.on_commit`:

   ```python
   from django.core.files.storage import default_storage
   from django.db import transaction


   class Datasets(PersonalData):
       ...

       def erase(self, user):
           queryset = self.get_queryset(user)
           names = [dataset.upload.name for dataset in queryset if dataset.upload]
           queryset.delete()
           transaction.on_commit(
               lambda: [default_storage.delete(name) for name in names]
           )
   ```

   `on_commit` runs the function only if the surrounding transaction commits, and straight away
   when there is none. If it fails, the account is still deleted: the failure is logged, and the
   person is told their account has gone.

3. Run `python manage.py check`. A kind that does not say how, while another does, is reported
   as `mvp_compliance.E009`, naming the kind's path.

## What counts as saying how

A kind says how it is deleted when it sets `erasure` or overrides `erase`. The property
`says_how_erased` reports it. A subclass of a kind that overrides `erase` inherits the
override; a subclass of a silent kind is still silent. A kind that says nothing raises
`NotImplementedError` from `erase()`, naming its class.

An `erasure` that is neither `PersonalData.DELETE` nor `PersonalData.WITH_ACCOUNT` is reported
as `mvp_compliance.E009`.

## Finding out whether deletion is offered

`deletion_offered()` in `mvp_compliance.personal_data` returns `True` only when the setting
lists at least one kind and every kind says how it is deleted. It returns `False`, and never
raises, when the setting is absent or empty, when a kind is silent, and when a kind cannot be
imported. The system check reports an import failure.

```python
from mvp_compliance.personal_data import deletion_offered

if deletion_offered():
    ...
```

`kind_path(kind)` returns the dotted path of a kind's class, the name the package uses for it
in errors and logs.

## What a person sees

Once deletion is offered, the account area has a **Delete account** page at `delete/` under
wherever the package's URLs are mounted (`mvp_compliance:delete-account`), served by
`mvp_compliance.views.DeleteAccountView`. Like the **Your data** page it needs `allauth.account`
and an account area, and sends a person who has not confirmed who they are recently to
django-allauth's own confirmation page first. A submission made before confirming is replayed
once they have, so they do not type their address twice.

The page lists the account and, in the order you declared them, each kind, as what will be
deleted. If acceptances survive the removal of an account, which is the default, the documents the
person agreed to are listed apart as what is kept: the record of each version, and when, stays as
evidence and no longer names the account. With
`MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL = False` they are listed as deleted. Where the
**Your data** page exists, the page links to it, so a person can keep a copy first.

To confirm, the person types their email address, or their username when the account has none,
into `DeleteAccountForm`. Case and surrounding spaces do not matter. The delete button stays
disabled until the entry matches. An empty or different entry that reaches the server anyway
shows an alert above the title and an error at the field, and deletes nothing.

A correct entry runs `mvp_compliance.deletion.delete_account(user, kinds)`: each kind's `erase` in
the order declared, then the account itself, in one transaction. The browser is signed out, and
so is every other browser signed in as the account, because the account no longer exists. The
person is sent to `mvp_compliance:account-deleted`, a page served by
`mvp_compliance.views.AccountDeletedView` that needs nobody signed in.

If any step fails, including a row of your own that refuses the deletion of the account, nothing
in the database is deleted and `delete_account` raises `AccountDeletionError`, whose `kind`
is the failing kind's dotted path, or `"account"` for the account itself, with the original
error as its cause. The page is shown again with an alert, the status is 500, the person stays
signed in, and the failure is logged at ERROR naming the kind. Files removed in
`transaction.on_commit`, as in step 2 above, go only after a deletion has committed.

The slugs `delete` and `deleted` are reserved, so no document can take either address.

## Hearing about each deletion

The package keeps no record that an account was deleted. If your site needs one, or needs to do
something afterwards such as send a last email, connect a receiver to
`mvp_compliance.signals.account_deleted`. It is sent once for each deletion, after the deletion
has committed, and never for one that could not be done:

```python
from django.core.mail import send_mail
from django.dispatch import receiver
from mvp_compliance.signals import account_deleted


@receiver(account_deleted)
def say_goodbye(sender, user, subject, kinds, **kwargs):
    send_mail("Your account has been deleted", "...", None, [user.email])
```

`user` is the deleted account. Its `pk` is `None` by then, and its other fields, such as the
email address, are as they were. `subject` is its primary key as text, the value every acceptance
it leaves behind carries, so `Acceptance.objects.for_subject(subject)` finds them. `kinds` is the
key of each declared kind that was deleted, in order. A receiver that raises is logged, and the
account stays deleted. Whatever your receiver keeps about the person is your project's own record,
kept under your project's rules.

Deleting an account removes the user's own row, which is a row of your project's user model. It
is the one thing the package deletes outside what a kind names.
