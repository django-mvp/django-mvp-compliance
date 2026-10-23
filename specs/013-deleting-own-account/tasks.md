# Tasks — 013 A person deletes their account and their data

Derived from [plan.md](./plan.md). Task ids are stable. Every task that changes behaviour follows
Article I: the failing test comes first. Tests find elements by fixture data, id or `data-` hook,
never by wording, and assert an error by its code or type, never by its sentence.

Documentation is written in the story that introduces the public name.

Tests that need declarations use the existing `tests/conftest.py` fixture that sets
`MVP_COMPLIANCE_PERSONAL_DATA` and reloads the URLconfs. Kinds for tests live in `tests/kinds.py`.

Order: US-2, then US-1 and US-3.

## Foundational

| Id | Task | Done when |
|---|---|---|
| T001 | Remove the sketch's `?state=` handling from `DeleteAccountView` and its unconditional `delete/` route (the route is re-added conditionally in T009); keep the templates, the form and `AccountDeletedView` | Full suite green; pre-commit green |

## US-2 — A developer says how the project deletes what it holds about a person (P1, issue #128)

| Id | Task | Done when |
|---|---|---|
| T002 | `tests/test_personal_data.py::TestErase` — a kind with `erasure = DELETE` deletes that user's rows from `get_queryset` and nobody else's (scenario 2, FR-015); `WITH_ACCOUNT` deletes nothing (scenario 3, FR-016); an overridden `erase` is the one called (scenario 4, FR-017); a kind saying nothing raises `NotImplementedError` from `erase`; `says_how_erased` is true for the first three and false for the last, true for a subclass of a kind that overrides `erase` and false for a subclass of a silent kind. `TestDeletionOffered` — false with the setting absent, empty, all silent, or mixed; false with an unimportable path and with a kind module that raises `ImproperlyConfigured` on import; true when every kind says how (scenarios 1, 5, FR-018) | Fails before T003 |
| T003 | `PersonalData.DELETE`, `WITH_ACCOUNT`, `erasure`, `erase()`, `says_how_erased`; `deletion_offered()`; `kind_path()`, used by `PersonalDataCopy.collect` | T002 passes |
| T004 | `tests/test_checks.py::TestErasureCheck` — mixed declaration: one E009 per silent kind naming its path; an `erasure` value that is not a constant: E009; all silent, or all saying how: no E009 (scenario 6, FR-019) | Fails before T005 |
| T005 | E009 in `check_personal_data`; messages translatable | T004 passes |
| T006 | Documentation for US-2: `docs/how-to/delete-an-account.md` (saying how, files with `on_commit`), pointer from the declaring how-to, `CONTEXT.md` *Declared kind*, `CHANGELOG.md` *Added* | Docs check green |

## US-1 — Deleting my account (P1, issue #127)

| Id | Task | Done when |
|---|---|---|
| T007 | `tests/test_deletion.py::TestDeleteAccount` — `delete_account` runs each kind's `erase` once in order and then removes the user (scenario 7, FR-009); a kind that raises leaves the user and every row of every kind, including rows an earlier kind deleted, in place and raises `AccountDeletionError` naming the kind with the original as its cause (scenario 12, FR-011); a user with a `PROTECT` row pointing at it (a test model) leaves everything in place and raises it naming `account`;  acceptances survive with `user` null under the default setting and are gone with it off (scenario 10, FR-013); another user's rows are untouched (scenario 11) | Fails before T008 |
| T008 | `mvp_compliance/deletion.py` `delete_account`; `AccountDeletionError` | T007 passes |
| T009 | `tests/test_views.py::TestDeleteAccountPage` — route and menu entry absent unless `deletion_offered()`, present when it is (scenario 1, FR-001, FR-018); anonymous GET and POST go to sign-in and delete nothing (scenario 4, FR-005); not reauthenticated: redirected to `account_reauthenticate` on GET and POST, nothing deleted (scenario 5, FR-006); GET lists the account, then each kind's key in order by `data-` hook, deletes nothing and calls no `erase` (scenario 2, FR-002, FR-003); the agreements key is in the kept card by default and in the deleted list with the setting off; the copy link is present (scenario 3, FR-004); a user with an unusable password and no authenticator reaches GET and POST without being sent to reauthenticate, and one who reauthenticated a moment ago is not sent again (scenario 5, FR-006); the route and menu expectations come from fixture kinds known to be silent or speaking, never from `deletion_offered()` itself; 404 with no account area and without `allauth.account`; the route takes no argument (FR-008) | Fails before T010 |
| T010 | `DeleteAccountView` context and the conditional route; `delete` and `deleted` in `Document.RESERVED_SLUGS` with one case beside the existing reserved-slug test | T009 passes |
| T011 | `tests/test_views.py::TestDeleteAccountSubmit` — an empty or wrong confirmation deletes nothing and shows the field error by its code (scenario 6, FR-007); the username is asked for when the account has no email; a POST made before reauthentication completes the deletion once allauth's confirmation replays it; a correct one (any case, surrounding spaces) deletes the account, every kind's rows, signs this browser out, and a second client signed in as the same account is anonymous on its next request (scenario 8, FR-010, SC-006); the deleted page answers 200 to an anonymous request; sign-in with the old details fails (scenario 9); a failing kind gives status 500, the alert by `data-` hook, the user still there and still signed in, and an ERROR log naming the kind with the original exception (scenario 12, FR-011, FR-012) | Fails before T012 |
| T012 | `DeleteAccountView.post` with `csrf_protect` on dispatch, the failure alert wired to a real failure | T011 passes |
| T013 | The demo per plan.md (`Profile` `WITH_ACCOUNT`, `Uploads` own `erase` with `on_commit` file removal, `leaving.user@example.com` in `seed_demo`). `CONSTITUTION.md` Article XIII amended to name the account and the rows a kind's own `get_queryset` names under `erasure = DELETE` (D8); ADR 0029. Documentation for US-1: `docs/how-to/delete-an-account.md` what a person sees and what survives, `README.md` section and docs list, `CONTEXT.md` *Account deletion*, `CHANGELOG.md` | `migrate` then `seed_demo` on an empty demo database; deleting `leaving.user@example.com` on the dev server works and removes its upload file |

## US-3 — A project hears about every account deleted (P3, issue #129)

| Id | Task | Done when |
|---|---|---|
| T014 | `tests/test_views.py::TestAccountDeletedSignal` — using `django_capture_on_commit_callbacks(execute=True)`: a receiver is called once per deletion, only from the commit callback, with the deleted user, its key as text and the kinds' keys (scenario 1, FR-021); not called when the deletion fails (scenario 2); a receiver that raises leaves the account deleted, the redirect intact, and is logged (scenario 3, FR-022); no row is written by the deletion beyond what the project's models do (FR-023) | Fails before T015 |
| T015 | `account_deleted` in `signals.py`, sent from the view in `transaction.on_commit` with `send_robust`; documented in `docs/how-to/delete-an-account.md`; `CHANGELOG.md` names what is passed to the project's code (Article XIV) | T014 passes; full suite green |
