# Implementation Plan: A person deletes their account and their data

**Branch**: `013-deleting-own-account` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

## Summary

Each kind declared in `MVP_COMPLIANCE_PERSONAL_DATA` gains a way to say how a person's records of
that kind are deleted: `erasure = PersonalData.DELETE`, `erasure = PersonalData.WITH_ACCOUNT`, or
its own `erase(user)`. When every declared kind says so, the account area gets a **Delete account**
page. It is guarded by django-allauth's `reauthentication_required`, lists what will be deleted and
what is kept, and asks the person to type their email address. On a valid submission it runs every
kind's `erase(user)` in declared order and then `user.delete()`, all in one transaction, signs the
browser out and redirects to a page saying the account has been deleted. A failure rolls everything
back, logs the failing kind and shows the page again with an alert. A signal, `account_deleted`,
tells the project after each deletion has committed. The approved sketch's templates are kept.

## Technical context

Python 3.12+, Django 5.2 to 6.1. No new dependency: django-allauth is already the `personal-data`
extra (FS-012). No package model and no package migration. Tests with pytest and pytest-django,
settings `tests.settings`.

## Constitution check

- **Article I, testing**: every task that changes behaviour starts from a failing test. Wording and
  layout are not tested. What is deleted, what survives and who is signed in are.
- **Articles II and III, simplicity**: one attribute, one method, one view, one form, one signal,
  one check message. No registry and no new setting: the declarations are the switch (D2).
- **Article XI**: acceptances are never written to. The deletion leaves them to
  `keep_or_remove_acceptances`, unchanged.
- **Article XIII**: amended in this branch to name the one removal the package makes itself, the
  signed-in person's own account (D1, ADR 0029). Every other row is deleted only by the project's
  `erase`. No wording claims completeness or names a regulation.
- **Article XIV**: nothing is stored. The signal passes the deleted user and its key to the
  project's own code, which gets a CHANGELOG entry naming them.
- **Article XV**: a project whose kinds say nothing about deletion sees no page, no route and no
  menu entry, and its copy works as before.

## Design

### Saying how a kind is deleted

```python
from mvp_compliance.personal_data import PersonalData


class Uploads(PersonalData):
    heading = _("Files you uploaded")
    model = Upload
    fields = ["title", "licence", "uploaded", "file"]
    erasure = PersonalData.DELETE  # get_queryset(user).delete()

    def get_queryset(self, user):
        return Upload.objects.filter(owner=user)


class Profile(PersonalData):
    ...
    erasure = PersonalData.WITH_ACCOUNT  # removed by the account's own deletion


class Subscriptions(PersonalData):
    ...
    def erase(self, user):
        cancel_subscriptions(user)
```

On `PersonalData`:

- `DELETE = "delete"` and `WITH_ACCOUNT = "with-account"`, class constants.
- `erasure: str | None = None`.
- `erase(self, user) -> None`: `DELETE` → `self.get_queryset(user).delete()`; `WITH_ACCOUNT` →
  nothing; otherwise raises `NotImplementedError` naming the class.
- `says_how_erased` (a property): `self.erasure is not None or type(self).erase is not
  PersonalData.erase`.

`AgreementsPersonalData` is never erased by this route and never part of the check.

A module-level `deletion_offered() -> bool` in `personal_data.py`: the setting is a non-empty list,
every path imports to a `PersonalData` subclass, and every kind says how it is erased. It returns
`False` rather than raising on a path that cannot be imported, which the check reports.

### The check

`check_personal_data` gains `mvp_compliance.E009`: when at least one declared kind says how it is
erased, one error per kind that does not, naming its path, with a hint naming `erasure` and
`erase()`. An `erasure` value that is neither constant is also E009. No error when no kind says
anything.

### Deleting

`mvp_compliance/deletion.py`, one function, because the view and a project's own management code
should run the same thing:

```python
def delete_account(user, kinds) -> None:
    with transaction.atomic():
        for kind in kinds:
            try:
                kind.erase(user)
            except Exception as error:
                raise AccountDeletionError(path_of(kind)) from error
        user.delete()
```

`AccountDeletionError(kind)` in `exceptions.py`, beside `PersonalDataError`, carrying the kind's
dotted path. A failure in `user.delete()` itself raises it with the kind `"account"`. Because the
`raise` happens inside the `with`, the transaction rolls back before the caller sees it.

### The page

`DeleteAccountView` in `views.py`, kept from the sketch with its approved template, minus the
`?state=` handling:

- `dispatch`: 404 with no account area or without `allauth.account`, exactly as `PersonalDataView`.
- `get` and `post` decorated with `reauthentication_required`; `LoginRequiredMixin`.
- Context: `sections` (declared kinds, then `AgreementsPersonalData()` when acceptances do not
  survive), `kept` (`AgreementsPersonalData()` when they do), `form`, `copy_url` when
  `mvp_compliance:personal-data` reverses, `account_center_url`.
- `DeleteAccountForm` from the sketch: the email address, or the username when the account has
  none, compared ignoring case and surrounding spaces.
- `post`: invalid form → page with the field error, nothing deleted. Valid → capture
  `subject = Acceptance.subject_of(user)` and the kinds' keys, call `delete_account`. On
  `AccountDeletionError` log at ERROR with the kind and the original exception, and render the page
  with `failed=True`, status 500. On success `logout(request)`, send `account_deleted` with
  `send_robust`, log any receiver's exception, and redirect to `mvp_compliance:account-deleted`.

`AccountDeletedView`, from the sketch, needs nobody signed in.

Routes in `urls.py`: `deleted/` always; `delete/` only when `deletion_offered()`. The menu entry is
already in `menus.py` and follows the route.

### The signal

`account_deleted` in `signals.py`. Sender: `DeleteAccountView`. Arguments: `user` (the deleted
instance, `pk` now `None`), `subject` (its key as text), `kinds` (each declared kind's key, in
order).

### The demo

`demo/personal_data.py`: `Profile` says `WITH_ACCOUNT`. `Uploads` overrides `erase` to delete the
person's rows and, in `transaction.on_commit`, their files from storage, as the documented pattern
for files. `seed_demo` adds `leaving.user@example.com` with an upload and an acceptance, so the
walkthrough can delete an account without losing the standard ones; running `seed_demo` again
recreates it.

### Documentation

- `docs/how-to/delete-an-account.md`: offering deletion, the three ways a kind says how, files with
  `on_commit`, what happens to acceptances, the signal, and that it removes the account itself.
- `docs/how-to/declare-what-the-project-holds-about-a-person.md`: a pointer to it.
- `README.md` section and docs list, `CONTEXT.md` *Account deletion* and *Declared kind*,
  `CHANGELOG.md` *Added*.
- `CONSTITUTION.md` Article XIII amended; `docs/adr/0029-the-package-removes-the-persons-own-account.md`.

## Story order

US-2, then US-1 with US-3. They edit the same modules and are built one after another.
