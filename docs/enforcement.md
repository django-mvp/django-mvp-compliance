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
2. If no enforced document is outstanding for them, the request is served, and the finding is
   remembered.
3. If the page that asks has no address, the request is served. The
   [system checks](#the-system-checks) report that.
4. If the address asked for is [kept reachable](#what-stays-reachable), the request is served.
5. Otherwise they are stopped: the view of the address they asked for does not run, and they are
   sent to the page that asks, `mvp_compliance:agree`.

A person with two enforced documents outstanding is sent once, to the one page, which lists both.

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

"Beneath" is read a path segment at a time: `/static/` covers `/static/site.css` and does not
cover `/staticfiles/site.css`.

Nothing else is kept reachable. The admin is stopped like any other address, and so is an address
that resolves to nothing.

`AgreementMiddleware.is_reachable(request)` is what answers it. It compares `request.path` with
the page that asks and with the two settings, and resolves `request.path_info`, as Django's own
URL resolution does, for the package's pages and the sign-out names.

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
checks report two misconfigurations, each an error that names what to change. `manage.py check`
runs them, and so do `runserver` and `migrate`:

| Id | Reported when | What to do |
|---|---|---|
| `mvp_compliance.E001` | The page that asks has no address, because the package's addresses are not mounted. | Add `path("legal/", include("mvp_compliance.urls"))` to the project's URLconf. |
| `mvp_compliance.E002` | No entry before the middleware is `AuthenticationMiddleware` or a subclass of it. | List the middleware after the one that identifies the signed-in user. |

A subclass of `AuthenticationMiddleware` counts, so a project with its own does not need to
change anything. Left unfixed, the first means no request is stopped, because the middleware
does not redirect anybody to an address that does not exist, and the second means it finds
nobody signed in. Either way the check holds nobody, which is why both are errors.

Nothing is reported while the middleware is not listed, whatever else is wrong.
