# Decisions — 001 Legal documents kept as versioned records

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — No retirement of a document

**Ambiguous**: a site drops a document it no longer offers, for instance a user agreement that has
been folded into the terms. Nothing in the roadmap says what happens to it.

**Chosen**: documents are not retired in this feature, and a document with published versions
cannot be deleted at all.

**Why defensible**: no roadmap item from R1 to R11 asks for it, so building it now is speculative.
The absence is also safe in the direction that matters: the failure mode of having no retirement is
a longer list of documents, while the failure mode of having retirement is a route that could take
published wording out of reach of somebody entitled to read it. If retirement arrives later it adds
a state to the document rather than changing anything specified here.

One consequence worth naming: `CONTEXT.md` has no word for a document that is no longer offered,
and both *archived* and *retired* sit on the avoid list under **Superseded**. Whoever specifies
retirement picks the word then.

## D2 — The package assigns version order, and there is no author-supplied label

**Ambiguous**: whether an author names a version ("v2.1", "January 2026 revision") and whether that
name has anything to do with ordering.

**Chosen**: order belongs to the package. No author-supplied label exists in this feature.

**Why defensible**: `django-termsandconditions` carries a `version_number` field that authors fill
in while the version actually in force is computed from a separate date field, so the number orders
nothing and can disagree with reality. Two sources of truth for ordering is the specific defect
worth avoiding. A human-readable label was raised and left out because it has no consumer yet.
Support staff and complaint responses need one, so it is likely to arrive with R10, where the
people needing it appear.

## D3 — Publication takes effect immediately

**Ambiguous**: whether a version can be prepared now and dated to take effect later, which is how
`django-termsandconditions` works and a recognisable need for a policy with a notice period.

**Chosen**: publishing takes effect the moment it happens.

**Why defensible**: a scheduled publish means the version in force is computed from a clock rather
than stored, which makes "which version was in force at the instant this person agreed" a
calculation rather than a fact. That calculation is exactly what the evidence property cannot
afford. It also weakens publishing as a deliberate act, which issue #5 depends on. A site needing a
notice period can publish on the day, and a later feature can add scheduling as a queued act that
still resolves to a stored state.

## D4 — No rollback to an earlier published version

**Ambiguous**: whether a bad publish can be undone by making the previous version current again.

**Chosen**: no. Restoring earlier wording means publishing that wording again as a new version.

**Why defensible**: a rollback makes publishing two-way and breaks the one-way rule the package
exists to provide. It also destroys the history: a document whose current version moves backwards
has no honest answer to "what was in force in March". Republishing the old wording costs one
version and leaves a truthful record of what happened.

## D5 — No screens, no addresses

**Ambiguous**: whether a model-layer feature registers anything in the admin, given that without a
surface nobody can exercise it by hand.

**Chosen**: nothing. No admin, no forms, no views, no URLs.

**Why defensible**: the authoring surface is issue #5 and the reading surface is R2, both of which
follow immediately. An admin registration here would be written to be replaced, and the throwaway
version is the one that tends to survive. Tests exercise the rules, and they are the right consumer
for a feature whose entire value is a set of invariants.

## D6 — Deleting a document that has published versions is refused

**Ambiguous**: the constitution forbids editing a published version but says nothing about deleting
the document above it, which would take the versions with it.

**Chosen**: the package offers no way to delete a published version, and no way to delete a
document holding any.

**Why defensible**: an immutability rule with a cascade underneath it is not an immutability rule.
This closes the loophole rather than adding a policy, and it follows from Article XII rather than
extending it. A document created by mistake and never published can still be deleted, because
nothing has been put in front of anybody.

## D7 — Empty rendered output is refused at publication

**Ambiguous**: what happens when authored markup produces nothing, for instance a version whose
entire body is a comment.

**Chosen**: publication is refused.

**Why defensible**: an empty document in force is indistinguishable from a bug, and the alternative
is a site with a privacy policy page showing nothing while acceptance records accumulate against
it. Refusing at publication is the cheap moment to catch it, and it cannot be caught later because
a published version cannot be corrected.

## D8 — A document holding any version cannot be deleted, not only one holding published versions

**Ambiguous**: D6 settled that a document with published versions cannot be deleted and that a
document created by mistake and never published still can. It did not settle how, and the two
available mechanisms differ in what they protect.

**Chosen**: the version's foreign key to its document uses `on_delete=PROTECT`. A document holding
any version at all — draft or published — refuses deletion. A document created by mistake is
deleted by discarding its drafts first, which FR-005 already allows, and then deleting it.

**Why defensible**: the alternative is `CASCADE` plus an override on `Document.delete()` and
another on the queryset's `delete()`, because `QuerySet.delete()` never calls `Model.delete()`. That
is two overrides and a third route — a cascade reaching the document from somewhere else — that
neither of them covers. `PROTECT` is enforced by Django's deletion collector on every route
including that third one, and it is part of the field rather than of the model class, so the
historical model inside a migration carries it too.

The cost is one extra step for a case that should be rare: deleting a document that still holds a
draft. The benefit is that the route which destroys published wording does not exist to be missed.
The two failure modes are not comparable — one is mild inconvenience, the other is the loss of the
evidence this package exists to keep.

## D9 — Refusals raise package exceptions, not `ValidationError`

**Ambiguous**: Django's house style for a rejected write is `ValidationError`, and a later feature
will present these refusals in a form, which is what `ValidationError` is built for.

**Chosen**: two exception classes of this package's own — `PublishedVersionError` for an attempt to
change or delete a published version, `PublishError` for a publication refused.

**Why defensible**: `ValidationError` means "this input was not acceptable, tell the person and let
them try again". Neither of these is that. An attempt to rewrite published wording is a breach of
the invariant the package exists to hold, and a caller that catches `ValidationError` broadly —
which form and admin code does by design — would swallow it into a field error, which is the silent
discard FR-012 exists to forbid. Issue #5 builds the authoring screens and can translate either
exception into a form error deliberately, at the one layer where a person is actually being asked
to fix something.

## D10 — One route stays open, and it is one this package writes rather than offers

**Ambiguous**: FR-011 requires the rule to live with the data rather than with any one caller, and
names data migrations the package ships. Django's historical models are rebuilt from migration
state and do not carry a model's custom `save()`, so no model-layer guard can reach them.

**Chosen**: the manager is declared `use_in_migrations`, which closes the bulk routes inside a
migration. The one remaining route — a shipped data migration calling `save()` on a historical
instance — is closed by not writing one, and a test asserts no shipped migration writes to a
published version.

**Why defensible**: the route that remains is not a route the package offers anybody. It is
available only to code inside this repository, written by the people who set the rule, reviewed like
any other code and now covered by a test that fails if someone writes one. Closing it properly means
shipping database triggers, which means maintaining the DDL in three dialects and having no answer
for whatever backend a host project brings. The residue is named here rather than left for somebody
to discover, because an immutability claim with an unstated exception is worse than a stated one.

## D11 — On MySQL, the row lock holds FR-007 alone, and that is recorded rather than assumed

**Ambiguous**: the plan holds "at most one version in force" with a partial unique index and treats
it as the guarantee. Partial indexes are not universal.

**Chosen**: both mechanisms ship — the partial unique constraint and a `select_for_update()` row
lock inside `publish()`'s transaction — and which one carries depends on the backend the host
project runs.

| Backend | Partial unique index | Row lock |
|---|---|---|
| SQLite | enforced | ignored, and unnecessary: writers already serialise |
| PostgreSQL | enforced | real |
| MySQL / MariaDB | **not created** | real, and the only thing holding the rule |

**Why defensible**: MySQL and MariaDB support neither partial indexes nor a filtered unique
constraint, and Django does not fail when asked for one — it raises system check `models.W036` and
omits the constraint (`django/db/backends/mysql/features.py:45`,
`django/db/models/constraints.py:392-405`). Removing the constraint to make every backend behave
alike would give up a real database guarantee on the two backends that can provide it, to buy
nothing. Keeping it and saying nothing would leave a MySQL-backed project believing in a guarantee
it does not have. So both ship and the difference is written down.

What a MySQL-backed host project loses is the backstop, not the behaviour: the lock serialises
publishes through `publish()`, which is the only route this package offers, so two concurrent
publishes still leave exactly one version in force. What it does not survive is a write that reaches
the table by another road entirely — raw SQL, a second application, a bulk load. That is out of
reach on every backend, and one backend fewer has a net to catch it.

This repository's tests run on SQLite, which is where the constraint is exercised. Nothing here is
verified on MySQL, because nothing in this organisation runs MySQL; that is why this entry says what
is promised rather than the test suite implying it.
