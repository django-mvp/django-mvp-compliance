# Decisions — 010 Applying the agreement check across the whole site

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible. This specification was written without a round of questions to the maintainer, so
every reading of issue #87 that the issue did not state outright is recorded here, where it can be
overruled.

## The reading of issue #87 this specification is written to

A developer adds one middleware and the whole site is checked. A signed-in user who has not
accepted the current version of an enforced document is sent to the page from issue #86, with the
address they wanted. The page that asks, the package's other addresses, signing out and static and
media files stay reachable with no configuration, and a project lists more. Accounts are let past
by name in the settings or by a permission the package provides. Whoever manages the documents
sets enforcement per document in the admin. A user with nothing stopping them costs no database
query on ordinary requests, at the price of a short, configurable delay before a change reaches
them. It serves G3. The page itself, the kind of a document and the answer to what is outstanding
belong to #86, FS-007 and FS-003 and are not respecified.

## D1 — The check is switched on with a middleware, and is off without it

**Ambiguous**: the issue says "switch the check on for the whole site in one place" and does not
say where.

**Chosen**: one middleware added to the project's `MIDDLEWARE`. No separate on/off setting.

**Why defensible**: it is where an experienced Django developer looks for behaviour that applies
to every request, and Django's own `LoginRequiredMiddleware` set the pattern. A second setting
beside it would be two switches for one thing. Being off by default means an upgrade changes
nothing (FR-002).

## D2 — A new document is enforced

**Ambiguous**: the issue says publishing without enforcing is ordinary, and the glossary says off
is a legitimate answer. Neither says which a new document is.

**Chosen**: enforced, and existing documents become enforced on upgrade.

**Why defensible**: the middleware is already the deliberate switch, so this default stops nobody
until a developer acts. Once they do, a default of not enforced would fail silently: the site
looks protected and stops nobody, in a package whose essential goal is that a person is asked
before they continue (G3). The opposite failure, a document stopping people it should not, is
visible within minutes and fixed with one tick in the admin.

**Revisit if**: projects report being surprised by a cookie policy stopping their users on the day
they add the middleware. A warning on the publish confirmation page would be the next step, and is
a change to FS-002's page, not part of this feature.

## D3 — Enforcement does not change what is outstanding

**Ambiguous**: whether a document that is not enforced still counts as outstanding.

**Chosen**: it does. The check uses a narrower answer, enforced documents outstanding, which is
also available from code.

**Why defensible**: ADR 0009 already decided that outstanding carries no enforcement policy and
that the code which stops a request does the filtering. The account area and any later view of who
has agreed to what want the unfiltered answer. The issue says the same thing in its own words: an
outstanding acceptance "is left for them to give in their own time".

## D4 — What stays reachable by default

**Ambiguous**: the issue names "the page that asks, the documents themselves, signing out".

**Chosen**: every address the package serves (which covers the page that asks, the document pages
and the list of what a person agreed to), the address that signs a person out, and the site's
static and media files. The admin is not on the list.

**Why defensible**: static files are needed or the page that asks renders unstyled wherever the
application serves them itself, as in development. Covering all of the package's addresses avoids a
list that has to be extended each time the package gains a page. The admin stays checked because
staff are users too, and a project that wants otherwise adds one line or grants the permission.
How the sign-out address is found is for planning. django-mvp registers it under a known name, and
a project with its own sign-out lists the address.

## D5 — A project adds addresses, not views

**Ambiguous**: "a project should be able to add its own" could mean a list of addresses, a
decorator on a view, or both.

**Chosen**: a list of addresses in the settings. Each covers itself and everything beneath it.

**Why defensible**: the issue speaks of addresses, and a list also covers views the project does
not own, such as a payment callback in a third-party package, which a decorator cannot. One
mechanism is enough (Article II).

**Revisit if**: projects ask to exempt a single view of their own without knowing its address. A
decorator in the manner of Django's `login_not_required` is the obvious addition.

## D6 — Let past by name in the settings, or by a permission the package provides

**Ambiguous**: "either by name or by holding a permission" leaves open what a name is and whose
permission it is.

**Chosen**: names are the value an account signs in with, listed in the settings. The permission
is one the package provides. It is checked as Django checks any permission, so a superuser is let
past.

**Why defensible**: a fixed permission needs no setting and is granted to a group in the admin
with no deploy. A list of names suits the accounts a developer creates deliberately, such as a
monitoring account or a test account. Special-casing superusers out of an ordinary permission
check would surprise a Django developer more than letting them past, and it means the person who
can repair a misconfigured document is never locked out of the admin.

Being let past records nothing (FR-020). An acceptance is evidence that a person agreed, and
nobody agreed.

## D7 — A short delay instead of a query on every request

**Ambiguous**: "none of this should make every page slower" does not say what may be traded for
it.

**Chosen**: the finding that nothing stops a user is remembered for a delay the project sets, one
minute or less by default, with nothing permitted. A user who is being stopped is always checked
afresh.

**Why defensible**: the only alternatives are a database query on every request, which the issue
rules out, or a store shared by every process that is invalidated on publication, which the
package cannot assume a project runs. Comparable packages make the same trade with a cache
lifetime. Remembering only the clear answer keeps the two guarantees that matter: somebody who has
just agreed is let through at once, and somebody whose acceptance failed never is (FR-023).
Deciding whether an account is let past falls under the same rule, because checking a permission
costs queries of its own. Where the finding is kept is for planning.

## D8 — Submissions and requests for part of a page are stopped too

**Ambiguous**: the issue says "whatever they were trying to open" and does not mention a form
submission, or a request a page makes for part of itself.

**Chosen**: both are stopped. A submission is redirected without a return address. A request for
part of a page takes the user to the page that asks as a whole page.

**Why defensible**: letting either through would leave a way to keep using the site without
agreeing. A submission's address is not passed on because visiting it would not repeat the
submission and may not answer at all. django-mvp's pages make requests for parts of themselves, so
without FR-007 the page that asks would appear inside the page the user was on.

## D9 — A misconfigured check is reported, not left to loop

**Ambiguous**: the issue does not say what happens when the middleware is added but the page that
asks is not mounted, or the middleware is placed where the signed-in user is not yet known.

**Chosen**: the project's checks report it and name what to change (FR-009).

**Why defensible**: the alternatives are a redirect to nowhere for every user, or a check that
quietly stops nobody. Both are the kind of failure a developer finds in production.

## D10 — Visitors who are not signed in are never checked

**Ambiguous**: whether the check also demands a sign-in.

**Chosen**: no. A visitor who is not signed in passes untouched.

**Why defensible**: an acceptance names a user (glossary), so there is nobody to ask. Requiring a
sign-in is a separate decision the project already makes with Django's own tools.

## D11 — No design prototype

**Chosen**: the feature is built without one.

**Why defensible**: it adds no screen. The page a person is sent to belongs to issue #86. What
this feature shows is one field on the admin's document form and one column in its list, both in
places the admin already has for them.
