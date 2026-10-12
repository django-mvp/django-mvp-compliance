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
submission and may not answer at all. django-mvp offers views that answer htmx requests for parts
of a page, so without FR-007 the page that asks would appear inside the page the user was on.

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

## D12 — The page that asks lets a person go once the enforced documents are accepted

*Made in review of this specification.*

**Ambiguous**: the first draft left to FS-009 whether its page also offers documents that are not
enforced, and assumed the page would let a user through once the enforced ones were accepted.
FS-009 says otherwise: it sends a person on only when nothing is outstanding (its FR-008), shows
the page again after a partial agreement (FR-012), and passes straight through only a person with
nothing outstanding (FR-018). Its own decisions D1, D2 and D4 name this feature as the place where
that would be narrowed. Left alone, a user stopped over the terms who accepted them and left a
cookie policy unticked would be shown the page again and never returned.

**Chosen**: this feature amends those three requirements (FR-028 to FR-030). A person is sent on
once every enforced document outstanding for them is accepted. Unenforced documents are still
offered on the page and are never required. FS-009's `spec.md` is edited in the pull request that
builds this feature, not on this specification's branch.

**Why defensible**: the check and the page must give the same answer to "may this person carry
on", or the two together form a loop. Enforcement does not exist until this feature, so FS-009
could not have said it. The amendment changes nothing on a site where every document is enforced,
which is every site until a compliance editor switches one off (FR-032).

## D13 — Opening the page with no address to return to shows the optional documents

*Made in review of this specification.*

**Ambiguous**: once a person with only unenforced documents outstanding is sent straight on, there
has to be some way for them to reach the page and accept one.

**Chosen**: the return address decides. With one, they are sent straight on (FR-030). With none,
the page is shown (FR-031), and after they submit it they go to the default destination whatever
they agreed to. A person with nothing outstanding at all is sent on either way, as before.

**Why defensible**: an address to return to means the person was on their way somewhere and
should not be held up over something optional. No address means they opened the page on purpose.
It needs no extra parameter and no second page. The site-wide check cannot land anybody in the
no-address case by accident, because it only sends people with an enforced document outstanding,
and they are shown the page in every case.

**Revisit if**: FS-009's prototype gives optional documents a place of their own, such as the list
of what a person agreed to in the account area.

## D14 — The finding is kept in the session

*Made in planning.*

**Ambiguous**: decisions.md D7 leaves open where "nothing stops this user" is remembered.

**Chosen**: in the user's session, as the time the finding was made.

**Why defensible**: the specification assumes Django's sessions, and telling a signed-in user from
a visitor already loads the session, so reading the finding costs no further query. Signing in as somebody else and signing
out both flush the session, so the finding never passes between accounts. The cache framework's
default backend is per-process, which would make the delay depend on which worker answers.

**Revisit if**: a project runs without sessions.

## D15 — An account let past by the permission is asked about on every request

*Made in planning.*

**Ambiguous**: FR-021 says deciding whether an account is let past is covered by the delay. US-5
scenario 5 says an account whose permission is taken away is redirected on its next request.
Remembering that an account was let past would break the second.

**Chosen**: the permission is asked only of a user the outstanding query has just said would be
stopped, and the answer is not remembered. A user with nothing enforced outstanding is found clear
before the permission is ever read, so for them it costs nothing (US-5 scenario 6).

**Why defensible**: both statements hold as written. The cost falls only on a permission holder
who has an enforced document outstanding, which lasts until they accept it. An account named in the
settings costs nothing at all, and the documentation recommends that for automated accounts.

**Revisit if**: a site lets a large group past by the permission and never has them accept.

## D16 — Only an htmx request is recognised as a request for part of a page

*Made in planning.*

**Ambiguous**: FR-007 speaks of "a request for part of a page". Nothing marks such a request in
general.

**Chosen**: a request carrying `HX-Request: true` is answered with an `HX-Redirect` header and no
return address. A boosted link, which is an htmx `GET` for a whole page, keeps its return address.
Any other request made by a script gets the ordinary redirect.

**Why defensible**: htmx is what django-mvp's own views offer for partial requests, and its header
is the only dependable signal. The address of a fragment is not somewhere to return a person to, so
none is passed (FR-004). The documentation says what a project using another library sees.

**Revisit if**: django-mvp adopts another way of loading parts of a page.

## D17 — The stories are built in dependency order

*Made in planning.*

**Chosen**: US-2, then US-1, then US-3, then US-4 to US-6 in one piece of work.

**Why defensible**: the check asks a question only the field can answer, so the field comes first.
US-4, US-5 and US-6 each add one setting to the same class and the same documentation page, and
building them apart would have three pieces of work editing the same two files.

## D18 — What the design review changed, and what it did not

*Made after the design review.*

**Changed in the plan**: one FS-009 test is removed, because it records the rule FR-030 replaces
(T001). An unset `MEDIA_URL` covers nothing, since Django returns it as the site root. The demo
lists no reachable address, because its landing page is the site root. The finding is stored as the
time it was made, a number. A boosted htmx link keeps its return address. A third system check
refuses a string where either list setting wants a list. Tests that could only fail by renaming a
key, or that restated `list_display`, are replaced by tests of what happens.

**Kept**: the settings are named `..._EXEMPT_USERS` and `..._EXEMPT_URLS`, though the specification
says "let past" and "kept reachable". *Exempt* is the word Django projects already use for a list
of this kind in their settings, and the documentation uses the specification's words to explain
them.

**Why defensible**: every change is an edit to the plan or a task, made before any code exists.
None alters what the specification asks for.

## D19 — US-2: how the demo seed marks House rules, one test left failing, and a page outside the tasks

**Decision**: `seed_demo` marks House rules as not enforced with an `update()` at the end of
`handle()`, beside the one that makes Delivery information a notice, rather than passing the choice
when the document is created. `tests/test_models.py::TestDocument::test_document_holds_no_wording`
asserts that the concrete fields of `Document` are exactly `id`, `name`, `slug` and `kind`; it fails
now that there is a fifth field, and it was left as it was.

**Why**: a demo seeded before the field existed already holds House rules, and creating it with the
choice would skip it ("already seeded"). The `update()` reaches both. The test is not one this story
wrote, and the rules for a story forbid changing one; the edit it needs is to add `enforced` to the
set it compares with, which is for whoever triages the story.

`docs/authoring.md` is edited too, though no task names it: its page on the documents list and a
document's form would otherwise leave out the new column and field.

**Revisit if**: the test is changed to say what it is for, that a document holds no wording, in a
way that does not list every field.
