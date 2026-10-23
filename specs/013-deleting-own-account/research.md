# Research — 013 A person deletes their account and their data

## Planning notes

### N1 — The declaration that serves the copy serves deletion

**Adopted.** `PersonalData` (merged in FS-012) gains an `erase(user)` method and an `erasure`
attribute, and nothing in FS-012's design makes that awkward:

- A kind already takes a user and never a request, so `erase(user)` has the same shape as
  `collect(user)` and `get_queryset(user)`.
- `get_queryset(user)` already says which rows are the person's, so "delete them" needs no new code
  from the project: `get_queryset(user).delete()`.
- The setting is already the ordered list the page shows, so the deletion runs over the same list
  in the same order (FR-002, FR-009).

The three ways a kind can say it is deleted (FR-015 to FR-017) map onto the class like this:

| The kind says | Written as | `erase(user)` does |
|---|---|---|
| Its rows are deleted with the person | `erasure = PersonalData.DELETE` | `self.get_queryset(user).delete()` |
| Its rows go with the account | `erasure = PersonalData.WITH_ACCOUNT` | nothing |
| The project's own code deletes them | `erase(self, user)` overridden | the project's code |
| Nothing | neither | raises `NotImplementedError` |

A kind "says how it is deleted" when `erasure` is set or `erase` is overridden. Detecting an
override is `type(kind).erase is not PersonalData.erase`. An attribute alone would cover the first two rows
but would need a third value meaning "I overrode the method", which is the override test written
twice.

## Removing the account

`user.delete()` is Django's own deletion of the user. It runs every `on_delete` the project's
models declare, including `Acceptance.user`'s `keep_or_remove_acceptances` (ADR 0008) and
`Version.publisher`'s `SET_NULL`. allauth's `EmailAddress`, `SocialAccount` and `Authenticator`
rows all `CASCADE` from the user, so nothing of allauth's survives.

**All or nothing.** Every kind's `erase(user)` and `user.delete()` run inside one
`transaction.atomic()`. Any exception rolls the whole lot back, which is FR-011 for everything in
the database. The exception is caught outside the block, so the rollback has happened by the time
the page is drawn.

**Files.** Django never deletes a file from storage when its row goes, and nothing rolls a file
back. A kind that must remove files does it in `transaction.on_commit()` from its own `erase`, so
the files go only once the deletion has committed. That is Django's documented way to tie a side
effect to a commit, it answers decisions.md D3 better than documenting the risk, and the demo's
`Uploads` kind does exactly that so the pattern has a working example. The package itself never
touches storage.

## Signing out everywhere (FR-010)

`django.contrib.auth.get_user()` loads the user named in the session through the backend. Once the
row is gone, `ModelBackend.get_user` and allauth's `AuthenticationBackend.get_user` both return
`None`, and the request is anonymous. So every other browser the account was signed in to is signed
out on its next request without the package finding its sessions. The browser that made the
deletion calls `django.contrib.auth.logout(request)`, which flushes its session so nothing of it
remains. Session rows elsewhere keep an id that names no account, and expire as sessions do.

## Confirming identity, and confirming the deletion

The page is guarded on GET and POST by django-allauth's `reauthentication_required`, exactly as
`PersonalDataView` is (ADR 0028), so FR-006 is allauth's own rule, including treating an account
with nothing to confirm with as confirmed.

The separate confirmation (FR-007) is the field Sam asked for at the sketch: the person types the
account's email address, or its username when it has none, compared ignoring case and surrounding
spaces. It is an ordinary Django form, so its error is shown at the field by `c-mvp.form`.

## When the page exists

FR-018 and FR-019 are read at two points that already exist:

- **The route**: `mvp_compliance/urls.py` adds `data/` only while `MVP_COMPLIANCE_PERSONAL_DATA` is
  set. It adds `delete/` only while it is set, names at least one kind, and every kind says how it
  is deleted. A kind that cannot be imported is left to the system check, as for `data/`.
- **The menu entry**: the account area drops an entry whose address does not resolve
  (`mvp_compliance/menus.py`), so the entry follows the route with no code of its own.
- **The check**: `check_personal_data` gains `mvp_compliance.E009`, one per kind that says nothing,
  raised only when at least one other kind does say how. A declaration where none says anything
  stays valid: that is a project offering the copy alone.

The page after the deletion, `deleted/`, needs nobody signed in and holds nothing about anybody, so
it is always routed.

## What the page shows

- The account row is the package's own, always first.
- The project's kinds, by `heading` and `description`, gathering nothing.
- The agreements: in "what is kept" while `acceptances_survive_account_removal()` is true, and in
  "what will be deleted" otherwise.
- The link to the copy when `mvp_compliance:personal-data` reverses, which it does whenever the
  deletion page exists, since both need the setting. The template still checks, so a project that
  overrides the URLconf does not get a broken link.

## Telling the project (US-3)

A signal, `account_deleted`, beside `personal_data_copied`, sent with `send_robust` after the
atomic block has committed. Its arguments:

- `user`: the deleted instance. Django sets its `pk` to `None` after deletion, but its other
  attributes, such as the email address, are still there, so a project can send a last email.
- `subject`: the account's primary key as text, the value every surviving acceptance carries
  (`Acceptance.subject_of`), so a project can find what it kept.
- `kinds`: the key of each declared kind, in order.

Not sent when the deletion failed. A receiver that raises is logged and changes nothing (FR-022).

## The constitution and an ADR

Article XIII says the package never deletes data held in another application's models. Removing
the account is exactly that, and Sam chose it at the grill (decisions.md D1). The article gains one
sentence naming the exception: the signed-in person's own account, at their request, after every
kind the project declares has run its own deletion. ADR 0029 records the decision, why the
alternative was not taken, and that every other row the project holds is still reached only through
the project's code.

## What already exists

| New piece | Where the search stopped | Found |
|---|---|---|
| Listing kinds without gathering | this repo | `PersonalDataView.get_kinds`, `get_personal_data()` |
| "Delete this person's rows" | this repo | `PersonalData.get_queryset(user)` then Django's `QuerySet.delete()` |
| Identity confirmation | an installed package | allauth `reauthentication_required` |
| All-or-nothing deletion | Django | `transaction.atomic()` |
| Removing files only on success | Django | `transaction.on_commit()` (in the kind's code, not the package's) |
| Signing out everywhere | Django | the user row's absence, plus `logout(request)` |
| Acceptances with the account | this repo | `keep_or_remove_acceptances` (ADR 0008), unchanged |
| Type-to-confirm field and its error | Django | `forms.Form`, rendered by `c-mvp.form` |
| Account-area page shell, menu entry | this repo, django-mvp | `mvp/account/base.html`, `AccountCenterMenu` (already wired in the sketch) |
| Error naming the failing kind | this repo | the shape of `PersonalDataError`: a new `AccountDeletionError(kind)` beside it |
| Notice to the project | this repo | `personal_data_copied` with `send_robust`, copied |
| Erasure attribute and `erase()` | new code | none found |
| Check E009 | this repo | `check_personal_data`, extended |
