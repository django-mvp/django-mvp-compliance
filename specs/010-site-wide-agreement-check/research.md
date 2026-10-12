# Research — 010 Applying the agreement check across the whole site

The evidence behind the choices in [plan.md](./plan.md). Citations are to the packages the project
resolves in `.venv` (Django 6.1.1, django-mvp 0.25.1) and to this repository at `origin/main`
`a84554f`, which carries FS-009 as delivered.

There is no `planning-notes.md` and no `sketch.md` for this feature. The specification names the
things planning has to settle, and each has a section here.

## What FS-009 delivered that this feature builds on

- `AgreementView` (`mvp_compliance/views.py`) lists what `Document.objects.outstanding_for(user)`
  returns and marks each entry with `is_optional(document)` (`views.py:228`), which answers no.
  `post()` already sends a person on when every remaining entry is optional, and `get()` redirects
  only when there are no entries at all (`views.py:319`).
- The page's address is `mvp_compliance:agree`, and the destination travels as `next`
  (`views.py:266`). A destination on another host, or the page itself, is replaced by
  `MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL`.
- FS-009's decisions D16 and D22 name this feature as the one that replaces the body of
  `is_optional()` and decides what a visit with only optional documents does.
- The demo routes `legal/agree/` to its own `DemoAgreementView` ahead of the package's include
  (`demo/urls.py`), so that address resolves outside the `mvp_compliance` namespace. The check has
  to treat it as the page that asks all the same.

## Where the check runs

A middleware class with `__init__(get_response)` and `__call__(request)`, the shape Django's own
middleware has. It needs `request.user`, so it sits after
`django.contrib.auth.middleware.AuthenticationMiddleware`. Deciding in `__call__` and not in
`process_view` means an address that resolves to nothing is treated like any other address and the
person is redirected, and never served a "not found" page from a site they may not use yet.

## Which documents stop a person

`DocumentQuerySet.outstanding_for()` (`models.py:94`) is one query with a subquery. Narrowing it
with `.filter(enforced=True)` keeps it one query, and `.exists()` on that is what the check asks.
A notice and a document with nothing in force are already left out by `outstanding_for()`, so
neither can stop anybody whatever its `enforced` says (FR-011).

The page that asks reads `outstanding_for()` once for everything it lists and takes each entry's
`enforced` from the row, so its required entries are by definition the rows the narrower queryset
returns. A test asserts the two sets are the same (FR-015).

## Where "nothing stops this user" is remembered

In the session, as the time until which the finding holds.

- The specification assumes Django's sessions (Assumptions), and
  `AuthenticationMiddleware` has already loaded the session to find the user, so reading one more
  key costs no query.
- Writing the key marks the session modified, so it is saved once, on the request that ran the
  check. That is the one request per delay SC-004 allows a query on.
- `django.contrib.auth.login()` flushes a session that belonged to a different user
  (`django/contrib/auth/__init__.py:187`) and `logout()` always flushes
  (`__init__.py:241`), so the finding never passes from one account to another.
- The cache framework was the alternative. Its default backend is per-process memory, which would
  make the delay depend on which worker answers, and the specification rules out assuming shared
  infrastructure (Clarifications, the delay).

Only the clear finding is stored (FR-023). A user who is being stopped has nothing stored and is
asked about on every request, so an acceptance lets them through on the very next one.

## What letting an account past costs

A name in the settings is compared with `user.get_username()` and costs nothing.

`user.has_perm()` reads the account's permissions from the database on first use in a request
(`django/contrib/auth/backends.py:174`). The check therefore asks it last, and only of a user the
outstanding query has just said would be stopped. A user with nothing enforced outstanding is never
asked, which is what US-5 scenario 6 and FR-021 require. A permission holder who does have
something outstanding costs the outstanding query and the permission read on each request until
they accept. That finding is deliberately not remembered: US-5 scenario 5 has an account whose
permission is taken away redirected on its next request. The documentation says a named account is
the cheaper of the two for an automated account.

A superuser passes `has_perm()` for every permission, so a superuser is let past (decisions.md D6).

The permission is declared in `Document.Meta.permissions`, beside `publish_version` on `Version`
(`models.py:460`), and is created by the same migration that adds the field.

## Which addresses stay reachable

Asked only about a user who would otherwise be redirected, so none of it costs anything for
anybody else.

- **The package's own addresses**: `resolve(request.path_info)` and a look at
  `match.app_names`. A path prefix would not do: a project that mounts the package at the root
  would make every address a package address.
- **The page that asks**: also matched by its path, `reverse("mvp_compliance:agree")`, because a
  project may route that address to its own subclass of the view ahead of the include, as the demo
  does.
- **Signing out**: by the name the address is registered under. django-mvp registers
  `account_logout` (`mvp/urls.py:57`), Django's own `django.contrib.auth.urls` registers `logout`,
  and the admin registers `admin:logout`. A project that signs people out anywhere else lists the
  address (spec, Edge Cases).
- **Static and media files**: `STATIC_URL` and `MEDIA_URL` when they are paths on this site. A
  value that names another host never reaches the application.
- **The project's list**: each entry covers itself and what is beneath it, compared a path segment
  at a time, so `/help/` covers `/help/faq/` and not `/helpful/` (US-4 scenario 4).

## A request for part of a page

django-mvp 0.25.1 ships an optional `HtmxFormMixin` (`mvp/views/htmx.py`) and loads no htmx of
its own. A project that uses it makes htmx requests, which carry the header `HX-Request: true`.
htmx follows a 3xx itself and swaps whatever comes back into the page, so a plain redirect would
put the page that asks inside the page the person was on. A 200 response with an `HX-Redirect`
header makes htmx navigate the whole window instead. The header is two lines to set, so the
package does not take `django-htmx` as a dependency for it (Article VII).

A request made by some other script cannot be told apart from an ordinary one. It gets the ordinary
redirect, and the documentation says so.

No return address is passed for an htmx request. The address asked for is a fragment, and
returning a person to a fragment is not returning them to where they were (FR-004).

## The return address

`request.get_full_path()` for `GET` and `HEAD`, passed as `next` and percent-encoded. Nothing for
any other method. `AgreementView.get_destination()` already refuses anything that is not on the
same host, so the middleware adds no check of its own.

## Reporting a misconfigured check

Django's system check framework, registered from `MvpComplianceConfig.ready()`. Two errors, each
raised only when the middleware is in `MIDDLEWARE`:

- the page that asks does not reverse, with the `include()` line to add;
- no `AuthenticationMiddleware`, or a subclass of it, comes before the check, with where to move
  it. Each earlier entry is imported and compared with `issubclass`, so a project's own subclass
  passes.

At run time the middleware lets a request through when `request` has no `user` or the page does not
reverse, so a misconfigured project stops nobody and loops nobody (US-1 scenario 12).

## The migration

`0001_initial` shipped in v0.1.0 and is fixed. This feature adds one migration, `0002`, holding
`AddField` for `enforced` with `default=True` and the `AlterModelOptions` that declares the
permission. A column added with a default gives every existing row that default, so every existing
document is enforced after upgrading and nothing else is touched (FR-024). No `RunPython`: the test
in `tests/test_migrations.py` that forbids one stays as it is.

## Time in tests

The repository has neither freezegun nor time-machine. The middleware reads the time through
`django.utils.timezone.now()`, which tests patch with `unittest.mock`. No dependency is added.

## The demo

The demo's `DEMO_OPTIONAL_DOCUMENT_SLUGS` and `DemoAgreementView.is_optional()` were FS-009's
stand-in for enforcement. They go, and the seed command sets `enforced=False` on the same document.
`DemoAgreementView.record_agreed()` stays, since it is how the failed write is shown. The demo's
settings gain the middleware, a named account and a listed address, and the seed command gains an
account that holds the permission through a group.
