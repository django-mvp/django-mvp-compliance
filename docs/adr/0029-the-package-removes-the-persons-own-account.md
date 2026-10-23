# ADR 0029 — The package removes the person's own account

**Status:** accepted

## Decision

`mvp_compliance.deletion.delete_account(user, kinds)` deletes the signed-in person's own account,
at their request, after every declared kind has run its `erase(user)`, all in one transaction. If
any step fails, including the removal of the account or the commit, nothing is deleted and the
caller gets `AccountDeletionError`, naming the kind or `"account"`.

The constitution's Article XIII is amended to name two deletions as the exception to "never
deletes data held in another application's models": the person's own account, and the rows a
declared kind's own `get_queryset(user)` returns when that kind sets
`erasure = PersonalData.DELETE`. The second is read through the same documented hook the copy of a
person's data already uses. Nothing else the project holds is deleted by the package; anything
further is the project's own `erase`.

A kind says how its records are deleted with `erasure = PersonalData.DELETE`, `erasure =
PersonalData.WITH_ACCOUNT`, or its own `erase(user)`. Deletion is offered only while every declared
kind says how, so the declarations are the only switch and there is no setting of its own.

## Why

The account is a row of the project's user model, so removing it is data in another application's
model. The alternative was to leave removing the account to the project's own code and check
afterwards that it is gone. A page that tells a person their account has been deleted should not
depend on each project remembering the last step, so the package removes it.

Two ready-made values cover the common cases with no code, and overriding `erase` covers the rest.
A single attribute would need a third value meaning "I wrote my own", which is the override said
twice, and a method alone would make every project write `get_queryset(user).delete()` by hand.

Tying the page to every kind saying how it is deleted means the page never promises more than the
deletion does, and a project that declared its kinds only for the copy is unchanged. Doing it in
one transaction means a failure costs the person nothing. Files held outside the database cannot be
rolled back, so a kind removes them in `transaction.on_commit` from its own `erase`, and the
package never deletes a file.

## Revisit if

A project needs the package to delete something the project holds without naming it through a
kind, or the user model is no longer one row the package can delete.
