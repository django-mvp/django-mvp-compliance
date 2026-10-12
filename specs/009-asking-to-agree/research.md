# Research — 009 Asking a signed-in person to agree to what is outstanding

The evidence behind the choices in [plan.md](./plan.md). Citations are to the packages the project
resolves in `.venv` (django-mvp 0.25.1) and to this repository at `origin/main` `b455695`.

## Planning notes

Each note in [planning-notes.md](./planning-notes.md), answered under its own words.

**"A list row carries no status badge."** Not adopted for this page. The review of the prototype
asked for "Required" and "Optional" as badges on each row, by name, which overrules the standing
rule here (sketch.md, *What was ruled by eye*). The rule stands everywhere else.

**"An alert goes above the page title."** Adopted. The three messages sit in `page_view.html`'s
`page.header` block, which django-mvp places above the title block.

**"A form never starts with a titled fieldset."** Adopted. The form holds a list and a button.
`c-form.field` draws a toggle as a label wrapped round its input, with no fieldset.

**"A reusable piece of a template is a Cotton component."** Adopted. The row is
`cotton/compliance/outstanding.html`, used once per document.

## What the prototype left to find a way to meet

### Recording several acceptances at a cost that does not grow

`Acceptance.objects.record()` (`models.py:872`) costs two notice checks, a read and a write for
each call, inside a savepoint, so a loop over it grows with the documents agreed to and breaks FR-023. The queryset already
has what a batch needs: `AcceptanceQuerySet.bulk_create()` (`models.py:773`) refuses a batch
naming a notice's version in one query, and the model has a unique constraint over
`subject` and `version` (`one_acceptance_per_person_per_version`). `bulk_create(...,
ignore_conflicts=True)` therefore writes every new acceptance and passes over one that already
exists, in one statement. The suite runs on SQLite. PostgreSQL does the same with `ON CONFLICT DO
NOTHING`. Oracle cannot ignore conflicts and raises, which the documentation says. That gives a batch the same guarantees
FS-003 gives one acceptance: one record per person and version, an existing record untouched, no
acceptance of a notice or of a draft. A manager method beside `record()` holds it, so FR-004's
"through the recording FS-003 provides" stays true.

`bulk_create()` does not call `save()` and sends no `pre_save`. Nothing in the package listens
for one.

### One submission stored together or not at all

One `bulk_create` is one statement up to the backend's batch size, about two hundred rows on
SQLite. Past that it is several, and the view's `transaction.atomic()` is what keeps FR-010.

### Knowing the record was written

After the write the view asks `Document.objects.outstanding_for(user)` again and decides from the
answer (FR-008). `outstanding_for()` is one query with a subquery (`models.py:94`), and
`in_force()` adds one prefetch for the current versions (`models.py:79`), so the page costs two
queries for its documents whatever their number.

### Which errors are a failed write

`django.db.DatabaseError` covers a database that cannot store the row. `RecordError` covers a
version that became a notice's between the page asking what is outstanding and the write. Both
leave nothing recorded. Anything else is a defect and is left to raise.

The list is not locked for the length of a request. A version replaced, or a document made a
notice, between the read and the write is not passed over by the write itself: an acceptance of the
version just replaced can be stored. It is a true record of what the person agreed to, it settles
nothing, and the second read keeps them on the page with the version now in force. Closing the
window would need a row lock SQLite does not have, and no requirement here asks for it
(decisions.md D19).

### Reporting the failure to the project

Django routes `logger.exception()` through the project's `LOGGING`. Under Django's default
configuration the `mail_admins` handler sits on the `django` logger only, so a record on
`mvp_compliance.views` reaches standard error and nothing else. A project that mails or forwards
its errors attaches a handler to that logger, and the documentation says so. The package logs on `mvp_compliance.views` at error level
with the traceback, and shows the person a fixed sentence (FR-011). No signal and no setting.

### The destination

`django.utils.http.url_has_allowed_host_and_scheme` is what Django's own sign-in view uses to
refuse an address on another host, and `django.shortcuts.resolve_url` turns a setting holding a
path or a URL name into an address. The parameter is `next`, the name Django's sign-in uses.
`LoginRequiredMixin` sends an anonymous visitor to sign in with the full path as `next`, query
string included, so the destination survives signing in with no code of ours (FR-007).

Django's `LOGIN_REDIRECT_URL` is not reused for the default: its own default, `/accounts/profile/`,
is an address most projects do not serve. The package's setting is
`MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL`, defaulting to `/`.

### The address and the slug

As FS-008 found for `agreed/`: a fixed route ahead of `<slug:slug>/` never answers with a
document, and `Document.RESERVED_SLUGS` with the `unreserved_slug` validator refuses the slug in
forms. The validator is unchanged and reads the set when it runs, so adding a member needs no
migration. `makemigrations --check` is clean with `agree` added.

### Required and optional rows

The approved page marks each row "Required" or "Optional", sends a person on once nothing required
is left, and reads "Continue" when nothing on it is required. Which documents are required is
decided by the site-wide check (#87), which is not built. Until it is, every outstanding document
is required, which is what this specification says. The view asks one method, per document,
whether it is optional, and the method answers no. The demo project overrides that method in its
own view so the approved screens stay reachable. The site-wide check replaces the method's body
when it lands. See decisions.md D16.

### The button's script

The repository has no JavaScript test runner and its testing standard names none. The standard does
list "ids, `data-` attributes and other hooks that a script depends on" as tested, so the form's
id, the `data-required` mark on each required toggle and the script's tag are asserted from
Python. The script's behaviour is checked at the walkthrough.

### Strings

`tests/test_views.py::TestPageStrings` lists the page templates by name and checks every string in
them against the English catalog. The new page template joins that list. The row component lives
under `templates/cotton/`, which the test's glob does not reach, so the test's list of files grows
to include it.

## Not needed

- No new dependency.
- No migration.
- No new model field, so Article XIV asks for nothing.
