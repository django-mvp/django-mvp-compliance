# Enforcement

A site that switches the check on sends every signed-in person who has not accepted the
current version of an [enforced](models.md#enforcement) document to the page that asks them to,
from any address on the site, and takes them back to the address they wanted once they have
agreed. No view is marked up, so the view somebody forgets is stopped too.

The check is one middleware. Without it nothing here happens: a project that does not add it
sends nobody anywhere.

## Switching the check on

Mount the package's addresses, so that the page that asks has an address
([Mounting the addresses](pages.md#mounting-the-addresses)), then list the middleware after
`AuthenticationMiddleware`:

```python
# settings.py
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "mvp_compliance.middleware.AgreementMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

It has to come after the middleware that identifies the signed-in user, because it reads
`request.user`, and it keeps what it finds in the session, so the project needs Django's
sessions. Which documents it holds a person to is each document's own choice: see
[Enforcement](models.md#enforcement) for `enforced`, and
[Enforced and outstanding](models.md#enforced-and-outstanding) for the question it asks.

## What it does to a signed-in person

For each request from a signed-in person, in this order:

1. If they were found to have nothing enforced outstanding less than a minute ago, the request
   is served. See [The delay](#the-delay).
2. If their sign-in value is in `MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS`, the request is served.
   See [Letting accounts past](#letting-accounts-past).
3. If no enforced document is outstanding for them, the request is served, and the finding is
   remembered.
4. If they hold the `mvp_compliance.skip_agreement` permission, the request is served.
5. If the page that asks has no address, the request is served. The
   [system checks](#the-system-checks) report that.
6. If the address asked for is [kept reachable](#what-stays-reachable), the request is served.
7. Otherwise they are stopped: the view of the address they asked for does not run, and they are
   sent to the page that asks, `mvp_compliance:agree`.

A person with two enforced documents outstanding is sent once, to the one page, which lists both.

The page also lists the documents that are not enforced and are outstanding for them, and sends
them on once the enforced ones are agreed to, so the page and the check let a person go at the
same moment. See [Asking a person to agree](pages.md#asking-a-person-to-agree) for what the page
does with a person who has only such documents outstanding.

A `GET` or `HEAD` carries the address they asked for, query string included, as `next`, so the
page sends them back to it once they have agreed. The address is percent-encoded, and the page
only follows an address on the same site ([Sending a person to the
page](pages.md#sending-a-person-to-the-page)).

Their acceptance takes effect on the very next request. Recording it is all the page does, and
a person who has just agreed is never asked about it again by a finding made earlier, because
only a finding that nothing stops them is remembered.

## Visitors who are not signed in

A visitor who is not signed in is never touched. Their requests are served as they would be
without the middleware, whatever the address, because an acceptance names a user and there is
nobody to ask. Requiring a sign-in is a separate decision, made with Django's own tools, such
as `login_required` and `LoginRequiredMiddleware`.

## What stays reachable

A person who is being stopped can still read the documents, sign out, and load the page that
asks with its styles, with no configuration. These addresses are kept reachable:

- the page that asks;
- every other address the package serves: a document's page, and the list of what a person
  agreed to;
- the address that signs a person out, when it is registered as `account_logout` (django-mvp's),
  `logout` (Django's own `LogoutView`) or `admin:logout`;
- the files beneath `STATIC_URL` and beneath `MEDIA_URL`. A setting that is unset, that names the
  site root (which is what Django returns for an empty `MEDIA_URL`), or that names another host,
  such as a CDN, covers nothing here, because a request to this site cannot be for a file on
  another.

- the addresses the project lists in `MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS`, which are added to
  these and never replace them. See [Keeping your own addresses
  reachable](#keeping-your-own-addresses-reachable).

"Beneath" is read a path segment at a time: `/static/` covers `/static/site.css` and does not
cover `/staticfiles/site.css`.

Nothing else is kept reachable. The admin is stopped like any other address, and so is an address
that resolves to nothing.

`AgreementMiddleware.is_reachable(request)` is what answers it. It compares `request.path` with
the page that asks and with the two settings, compares `request.path_info` with the project's
entries, and resolves `request.path_info`, as Django's own URL resolution does, for the package's
pages and the sign-out names.

## Keeping your own addresses reachable

A project has pages of its own that a person who has not agreed yet still needs: a help page, a
contact form, a status page. List them:

```python
# settings.py
MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS = ["/help/", "/contact/"]  # empty by default
```

The setting is a list of paths, written as the project's URLconf writes them. `request.path_info`
is what an entry is compared with, so a project served under a prefix leaves the prefix out.

- An entry covers itself and every address beneath it, a path segment at a time. `/help/` covers
  `/help/`, `/help` and `/help/faq/`, and does not cover `/helpful/`.
- An entry written without its trailing slash covers the same addresses as the one with it:
  `/help` and `/help/` are the same entry.
- An empty entry covers nothing.
- An entry of `/` covers every address, so listing it switches the check off for everybody. It
  stops nobody and is rarely what a project means. Remove the middleware from `MIDDLEWARE` to
  switch the check off on purpose.
- The setting is a list. A string, which would be read a character at a time and cover far more
  than was meant, is reported by [`mvp_compliance.E003`](#the-system-checks).

The addresses [listed above](#what-stays-reachable) stay reachable whatever the setting says, and
need no entry.

**Your own sign-out address.** The check recognises a sign-out address registered as
`account_logout`, `logout` or `admin:logout`. A project whose sign-out view is registered under
another name has to list its address here, or a person who has not agreed cannot sign out.

## Letting accounts past

Some accounts should never be stopped: the one a monitoring service signs in with, the ones a
browser test suite drives, a support team. There are two ways to name them, and an account that is
let past by either is served at every address, whatever it has outstanding.

**By the value it signs in with.** List it in the project's settings:

```python
# settings.py
MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS = ["monitoring"]  # empty by default
```

Each entry is compared with `user.get_username()`, so with a user model that signs in by email it
is the email address. A name that matches no account changes nothing, and neither does the account
being removed later. The setting is a list: a string, which would be read a character at a time, is
reported by [`mvp_compliance.E003`](#the-system-checks).

**By a permission.** An account that holds `mvp_compliance.skip_agreement`, directly or through a
group, is let past. An administrator gives the permission to a group in the admin, with no change to
the project's settings and no deploy, and takes it away the same way. An account whose permission
is taken away is stopped on its next request. A superuser holds every permission, so a superuser is
always let past. See [The permission to continue without
accepting](models.md#the-permission-to-continue-without-accepting).

Being let past records nothing. No acceptance is created, what is outstanding for the account is
unchanged, and the account can still accept a document itself on the page that asks.

Name only accounts whose sign-in value the holder cannot change, and remove a name when its
account is removed. A name is a claim about whoever signs in with it: if people can choose their
own username, or change it, somebody can take a name that is listed and is never stopped. A name
left in the setting after its account was removed is open to whoever registers it next.

### What it costs

An account named in the setting is let past before the database is asked anything, so its requests
cost what they would without the middleware. The permission is asked only of a person who has an
enforced document outstanding and is about to be stopped, so it costs nothing for anybody else, on
the request that makes the check and on those after it. A person who holds the permission is asked
about on every request, because the answer is not remembered, and that is what makes taking the
permission away take effect on their next request. The cost is the queries Django makes to read
that account's permissions.

## A form submission, and a request for part of a page

Letting either through would leave a way to keep using the site without agreeing, so both are
stopped.

**A submission.** A request that is not a `GET` or `HEAD`, such as a `POST`, `PUT`, `PATCH` or
`DELETE`, to an address that is not kept reachable does not reach its view. The person is
redirected to the page that asks with no `next`, because visiting the address would not repeat
the submission and may not answer at all.

**A request for part of a page.** django-mvp's views answer htmx requests for parts of a page,
and a redirect to the page that asks would be followed by htmx and placed inside the page the
person was on. So a request that carries `HX-Request: true` is answered with a `200`, an empty
body and the `HX-Redirect` header naming the page, which htmx documents as a client-side redirect
to that address, so the page that asks is loaded as a whole page
([htmx's response headers](https://htmx.org/reference/#response_headers)). It carries no `next`:
the address of a fragment is not somewhere to bring a person back to.

A link that htmx boosts is a `GET` for a whole page, which htmx marks with `HX-Boosted: true`
([htmx's request headers](https://htmx.org/reference/#request_headers)). It keeps its return
address, so `HX-Redirect` names the page with `next` set to the address asked for, as for any
other link. A boosted form submission is a `POST` and carries none.

Only an htmx request is recognised as a request for part of a page. Nothing marks one in general,
so a request made by a script with `fetch()` or by another library is answered with the ordinary
redirect, which the script follows as it would any other. A project that loads parts of a page
with something other than htmx should keep the addresses it requests reachable, or handle the
redirect in its script.

## The delay

Asking the database on every request would make every page slower, so a finding that nothing
stops a person is remembered in their session for sixty seconds, and in that time nothing is
asked. The finding is the time it was made, as a number of seconds, under the key
`mvp_compliance_clear_since` (`CLEAR_SINCE_KEY` in `mvp_compliance.middleware`), and the sixty
seconds is `CLEAR_FINDING_SECONDS` in the same module. A value in the session that is not a
number, or that is dated later than now, is treated as absent.

What follows from that:

- A person who is being stopped is asked about on every request, and the middleware writes
  nothing to their session, so one who has just agreed is let through at once, and one whose
  acceptance could not be recorded never is.
- A new version of an enforced document, or an enforcement switched on, reaches a person who was
  found clear within the minute. They are stopped on a later request, never in the middle of one
  that was already being served.
- Signing in as somebody else and signing out both flush the session, so a finding never passes
  from one account to another.

## What it costs a project

The middleware reads `request.user` on every request, and that reads the session. A view that
never touched the user or the session now has both read for it, and the session middleware marks
the response `Vary: Cookie` whenever the session was read. A page that a cache stored once for
everybody is stored once per cookie from then on, so a project that caches pages by address
alone should look at that before it switches the check on.

For a person found clear within the minute, the check adds no database query of its own. It
reads `request.user` and the session, which a view that reads `request.user` reads anyway.

## The system checks

When `mvp_compliance.middleware.AgreementMiddleware` is listed in `MIDDLEWARE`, Django's system
checks report three misconfigurations, each an error that names what to change. `manage.py check`
runs them, and so do `runserver` and `migrate`:

| Id | Reported when | What to do |
|---|---|---|
| `mvp_compliance.E001` | The page that asks has no address, because the package's addresses are not mounted. | Add `path("legal/", include("mvp_compliance.urls"))` to the project's URLconf. |
| `mvp_compliance.E002` | No entry before the middleware is `AuthenticationMiddleware` or a subclass of it. | List the middleware after the one that identifies the signed-in user. |
| `mvp_compliance.E003` | `MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS` or `MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS` is a string. | Write it as a list, even for one entry. |

A subclass of `AuthenticationMiddleware` counts, so a project with its own does not need to
change anything. Left unfixed, the first means no request is stopped, because the middleware
does not redirect anybody to an address that does not exist, and the second means it finds
nobody signed in. Either way the check holds nobody, which is why both are errors. The third
is reported once for each setting that is a string, because a string is read a character at a
time and would keep reachable or let past far more than was meant.

Nothing is reported while the middleware is not listed, whatever else is wrong.
