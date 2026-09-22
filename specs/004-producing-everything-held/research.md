# Research: Producing everything held about one person's acceptances

The questions the design rests on, each answered from the code on main, Django's own source, or
the constitution — never from recollection.

---

## R1 — Where can this surface live, when the package serves no address of its own?

**Question.** The spec assumes the answer is produced "by somebody who already works in the site's
staff surfaces, rather than at a new place of its own". This package registers no URLconf:
`tests/test_app.py::test_it_registers_no_public_urls` asserts `mvp_compliance.urls` does not exist,
and `demo/urls.py` says in a comment that the authoring surface lives entirely in the admin.

**Finding.** The Django admin is the only staff surface this package has, and it is the one FS-002
chose for authoring. Shipping a `urls.py` for the host project to include would add the first
address the package serves, contradict a test on main, and put the burden of mounting it — and of
mounting it behind something — on every consuming project.

The admin offers exactly two ways to add a page: a `ModelAdmin.get_urls()` extension, which is how
FS-002's preview and publish pages are mounted, and an `AdminSite` subclass, which a host project
would have to adopt. Only the first is available to a package.

**Consequence.** The page hangs off a `ModelAdmin`, which means it needs a model to hang off. R2
answers which.

---

## R2 — Which model hosts the page and the permission?

**Question.** `ModelAdmin.get_urls()` needs a registered model. The three candidates are `Document`,
`Version` and `Acceptance`, and a fourth option is a proxy model that exists only to name the act.

**Findings.**

1. **`Document` and `Version` are wrong on their face.** The page is about a person, not a document,
   and mounting it at `/admin/mvp_compliance/version/disclosure/` gives the admin index no entry at
   all, so nobody fielding a request would find it.

2. **Registering `Acceptance` itself is the option to avoid.** It would give every holder of
   `view_acceptance` a changelist of every acceptance the site holds — one person's consent history
   assembled and served to whoever has a routine staff permission, which is precisely the risk
   US-3 and `decisions.md` D2 exist to close. It is also the shape of R10, the site-wide picture,
   which this feature explicitly does not build.

3. **A proxy model gets its own content type and its own permissions.** Django's
   `create_permissions()` calls `ContentType.objects.get_for_models(*models,
   for_concrete_models=False)` and then walks `_get_all_permissions(model._meta)` per model
   (verified by reading `django/contrib/auth/management/__init__.py` in Django 5.2.17). So a proxy
   of `Acceptance` declaring `Meta.permissions` produces a permission attached to the proxy's own
   content type, not to `Acceptance`'s — and holding `view_acceptance` grants nothing on it.

**Answer.** A proxy of `Acceptance`, registered with an admin whose every permission hook keys on
the new permission and whose add, change and delete hooks all return `False`. The proxy carries no
table of its own, adds no column, and exists so that the act has a name, an address and a
permission. Its `verbose_name_plural` is what the admin index shows, so the index entry reads as
the question a person asks rather than as a model name.

Django does create the routine `add`/`change`/`delete`/`view` permissions for a proxy as well.
They are unavoidable and they grant nothing: the admin hooks below ignore them, and a test grants
every one of them to somebody and confirms the page still refuses.

---

## R3 — How is a person named, when a record can outlive their account?

**Question.** FS-003 stores two identifiers: `user`, a nullable foreign key cleared when the
account is removed, and `subject`, the account's primary key held as text and written once
(`models.py`, `Acceptance.subject_of()`). US-4 needs the answer to work when only the second
survives. But somebody fielding a request knows an email address, not a primary key.

**Findings.**

- `Acceptance.objects.for_subject(subject)` on main is already the lookup that works either way.
  `for_person(user)` is a thin call through `subject_of()` into it.
- `get_user_model().USERNAME_FIELD` names whatever the host project identifies accounts by; `email`
  is present on Django's own user model and on most replacements, but is not guaranteed.

**Answer.** One free-text field, and a resolution order:

1. Look for an account whose `USERNAME_FIELD` matches exactly. Found → the subject is that
   account's primary key as text.
2. Otherwise, if the user model has an `email` field, look for an account whose email matches,
   case-insensitively. Exactly one match → the subject is its primary key.
3. Otherwise, treat what was typed as the subject itself.

Step 3 is what makes US-4 reachable at all: a removed account has no row to look up, so the only
way to ask about that person is by the identifier their records still carry. It also means a
question about somebody the package has never heard of resolves to a subject with no records, which
is FR-005's answer rather than an error.

The ambiguity is real and small: an account whose username is literally another account's primary
key resolves as the account. Documented at the field, and the produced answer names the subject it
was produced for, so the person reading it can see which reading was taken.

---

## R4 — What makes the same answer twice identical?

**Question.** FR-006 and SC-005 require two productions with no change to the records to say the
same thing.

**Findings.**

- `Acceptance.Meta.ordering = ["accepted_at", "id"]` on main is already total: `id` breaks a tie, so
  the order is deterministic rather than merely usually stable.
- Everything an entry carries is stored: the document's name, the version's number, `accepted_at`,
  and `version.html`, which Article XIII fixes at publication.

**Answer.** Determinism is free, on one condition: **the answer carries no clock reading of its
own.** A "produced at" stamp on the page would make FR-006 false by construction. The page
therefore has none, and a test produces the same answer twice and compares.

That is a real cost — a printed answer does not say when it was produced — and it is the
specification's choice, recorded in `decisions.md`.

---

## R5 — One query, whatever the number of documents

**Question.** SC-008: the number of lookups must not grow with the number of documents a site runs.

**Finding.** Each entry needs the acceptance, its version, and that version's document. Django's
`select_related("version", "version__document")` resolves all three in one join.

**Answer.** `Acceptance.objects.for_subject(subject).select_related("version",
"version__document")`, materialised once. One query, whatever the number of documents, versions or
acceptances. Asserted with `django_assert_num_queries`, which the suite already uses for FS-003's
`outstanding_for()` bound.

---

## R6 — Serving the stored wording

**Question.** FR-007 puts each version's wording in the answer. `Version.html` is HTML, so the
template has to render it unescaped.

**Findings.**

- Article XIII: the HTML is produced once, at publication, through a sanitiser with an explicit
  allow list (`mvp_compliance/rendering.py`), and pages are served from the stored field.
- FS-002's preview and publish pages already render `version.html` unescaped, and
  `tests/test_admin.py::TestPreview` covers the stored-versus-fresh distinction.

**Answer.** Read `version.html` and mark it safe, exactly as the existing pages do. What must not
happen is re-rendering `version.markdown` at produce time: FR-010 forbids it, and a renderer
upgrade or an allow-list change would make the answer show something nobody was served.

A draft cannot appear here at all — `Acceptance.objects.record()` refuses a version that has never
been published — so there is no path by which an entry carries an empty `html`.

---

## R7 — What shape lets a further kind of record join?

**Question.** FR-017: the answer must be able to carry a further kind of record without its shape
changing, so the cookie choices in R8 join it rather than arriving as a second answer.
`decisions.md` D1 is equally explicit that no abstraction is built today for records that do not
exist, and that the requirement is a constraint on the design rather than a licence to build a
plugin system for one caller.

**Findings.** Two readings, and they differ:

- The answer is `{subject, acceptances}`. Adding cookie choices adds a field, so the shape changes
  and every consumer that walked the answer has to learn a second field name.
- The answer is `{subject, sections}` where a section is a named kind of record with its entries.
  Adding a kind adds a section, and nothing about the answer, the page or a consumer changes.

**Answer.** The second, with no registry, no hook, no setting and no entry point. The function that
produces the answer names each kind it knows about, and today it knows about one. A section carries
its heading and the template that renders its entries, so the page is a loop over sections and R8's
work is a dataclass, a builder line and a partial.

What this deliberately is not: anything a host project or another app can register into. That is
R11, it is aspirational, and FR-018 forbids it here.

---

## R8 — Does the answer carry the optional client address?

**Question.** FS-003 US-5 lets a project record the address a request came from, off by default.
FR-001 says the answer holds "everything it holds about them"; FR-003 names the document, the
version and the moment, and is silent about the address.

**Finding.** Where a site turned that setting on, the address is personal data this package holds
about that person, written into `Acceptance.ip_address`. An answer that silently omitted it would
be a partial answer presented as a complete one, which Article XIV names as worse than no answer.

**Answer.** The entry carries it, and the page shows it only where a record has one. No setting is
read at produce time — what governs the page is whether the record in front of it holds an address,
which is also what keeps records written before the setting was turned on looking exactly as they
did.
