# django-mvp-compliance

Domain model for django-mvp-compliance — legal documents, consent records and cookie consent for
projects built on django-mvp.

The terms below are the ones to use in issues, commits, tests, model names and templates. Several
exist to keep two things apart that ordinary English runs together: the document a person read, and
the record that they agreed to it. A bug report that confuses those two is unreadable.

## Core concepts

**Document**:
A named legal text that persists across rewordings — a privacy policy, a set of terms, a cookie
policy. It is the thing with a stable identity and a URL. A document holds no text of its own:
every word lives in one of its versions.
_Avoid_: policy (that names one kind of document, not the category), agreement, terms, page.

**Version**:
One revision of a document, holding the Markdown a person wrote and the HTML a reader was served.
A version is what acceptance points at, never the document, because "agreed to the privacy policy"
without a version is not evidence of anything. A version gets its number when it is published: the
year and its place among the document's versions published that year, such as 2026.2. A draft has
none.
_Avoid_: revision, edition, draft (that is a state a version can be in, not a synonym for it).

**Published**:
The state of a version that is live and immutable. Publishing is one-way: a published version is
never edited again, and a correction of any size means a new version. This is the constraint the
package exists to provide, and it outranks convenience everywhere it conflicts with it.
_Avoid_: active, live, released, final.

**Publisher**:
The account that put a version in force, kept on the version when it is published and never
changed after. It is recorded as the account and as that account's identifier, so a version can
still say "Account removed" once the account is gone, without naming anyone. A version
published from code with nobody named has no publisher, and says so.
_Avoid_: author (the person who wrote the wording may be someone else), approver, owner.

**Draft**:
A version that has never been published. It can be edited and previewed freely, and it is invisible
to everyone but the people who manage documents. A draft has no legal meaning at all.

**Current**:
The one published version of a document that a reader is served today and that acceptance is
measured against. Exactly one per document.
_Avoid_: latest (a draft can be more recent), active.

**Superseded**:
A published version that is no longer current. It stays readable at its own URL forever, because
someone accepted it and is entitled to see what they accepted.
_Avoid_: archived, expired, retired, old.

**Acceptance**:
The record that one user agreed to one version of one document, at a time. Immutable, like the
version it points at. An acceptance is a historical fact rather than a status: it is never edited
or withdrawn, and a user who accepts a newer version gains a second acceptance rather than
replacing the first.
_Avoid_: agreement, consent (that is the wider term below), sign-off, approval.

**Consent**:
The umbrella for everything this package records about what a person allowed — acceptances and
cookie choices together. Use it when both are meant, and the narrower word when only one is.

**Cookie choice**:
What a visitor decided about one cookie category. Distinct from an acceptance in two ways that
matter: it belongs to a visitor rather than a user, and it can be changed, because a person may
withdraw consent for cookies at any time.
_Avoid_: cookie consent (ambiguous between the choice and the mechanism), preference, opt-in.

**Cookie category**:
A group of cookies a visitor accepts or declines as one, because nobody makes that decision per
cookie. Analytics is a category.
_Avoid_: group, type, purpose, bucket.

**Visitor**:
Whoever is reading the site, signed in or not. Cookie choices belong to a visitor. Acceptances
cannot, because an acceptance names a person.
_Avoid_: anonymous user (a visitor may well be signed in), guest, session.

**User**:
A signed-in account, Django's `AUTH_USER_MODEL`. Acceptances belong to users and to nothing else.

**Compliance editor**:
Whoever is responsible for the wording of a site's legal documents — not assumed to be a
developer, an employee, or familiar with Markdown. Writes and publishes versions through the
admin's formatting-control editor.
_Avoid_: author (too generic — this package's other roles write things too), admin (names the
Django feature, not the person), legal team (an editor may be neither legal nor a team).

**Enforcement**:
Stopping a signed-in user who has not accepted the current version of a document from continuing,
and sending them somewhere they can read it and accept. Configurable per document, and off is a
legitimate answer: a cookie policy is usually published without being enforced.
_Avoid_: gating, blocking, guarding, interception.

**Host project**:
The Django project that installs this package. It owns the theme, the base template, its own user
model, and every piece of personal data this package does not hold.
_Avoid_: consumer, client, downstream, user (which means something specific here).

## Terms deliberately not used

**Compliant / compliance** (as a property of a site): the package name says what area it covers.
It never describes an outcome it cannot deliver. A feature makes something *recorded*,
*published* or *enforced* — never *compliant*.

**GDPR** (as a feature name): a regulation is not a feature, and naming one in code implies the
code satisfies it. Name the mechanism instead.

**Data subject access request / DSAR** (as something this package performs): it shows a person
what this package holds and offers hooks. It does not gather or erase data held elsewhere in the
host project, and no name here may suggest it does.

**Policy**: ambiguous between a legal document and a rule the code enforces. Say *document*, or
name the specific one.

**Banner**: names one possible presentation of the cookie consent flow. Say *cookie consent*, and
let the template decide what it looks like.
