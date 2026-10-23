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
   when there is none.

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
