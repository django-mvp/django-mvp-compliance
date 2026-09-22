# Research — 003 The record of who accepted which version

Six questions the design could not be written without answering. Each one names what was checked,
against which version, and what the answer means for the plan.

Django checked: 5.2.17, the floor this package supports, in the development virtualenv. Paths below
are relative to the installed `django/` package.

## R1 — How a setting can decide what happens to a record when its account goes

FR-013 asks for a setting that decides whether acceptances survive the removal of the account they
name. `on_delete` is an argument to `ForeignKey`, evaluated when the model class is built, so the
obvious reading is that a host project's setting cannot reach it: the class is built at import time,
and a project that flips the setting afterwards would be ignored.

That reading is wrong, and the mechanism it misses is the whole of this design. `on_delete` takes
**any callable** with the signature `(collector, field, sub_objs, using)` — that is all `CASCADE` and
`SET_NULL` are (`db/models/deletion.py:22` and `:69`). A callable of our own in that position is
invoked by the collector at the moment a delete runs, which is where the setting can be read:

```python
def keep_or_remove_acceptances(collector, field, sub_objs, using):
    if acceptances_survive_account_removal():
        SET_NULL(collector, field, sub_objs, using)
    else:
        CASCADE(collector, field, sub_objs, using)
```

Two consequences worth stating because neither is obvious.

**The system check for `SET_NULL` does not fire.** `ForeignKey._check_on_delete` compares
`on_delete == SET_NULL` by identity (`db/models/fields/related.py:1051-1064`), so a custom callable
that *delegates* to `SET_NULL` is invisible to it. The field still has to be `null=True` or the
database refuses the write at delete time rather than at check time, so the plan sets `null=True`
and says why.

**The setting is read per delete, not per process.** That is what makes the behaviour testable with
`override_settings`, and it means a project that changes its mind changes what happens next rather
than needing a migration.

**The callable is deliberately not given a `lazy_sub_objs = True` attribute, even though Django's
own `SET_NULL` has one** (`db/models/deletion.py:73`). The collector checks it at
`db/models/deletion.py:343` — `if getattr(on_delete, "lazy_sub_objs", False) or sub_objs:` — and an
ordinary callable without it has its `sub_objs` queryset evaluated before the call, which sends the
resulting field update down the `objs.extend(instances)` branch and a raw
`sql.UpdateQuery.update_batch()` rather than `combined_updates.update(...)` (`deletion.py:476-490`).

That routing is not on its own what decides whether this package's guard fires, and an earlier
reading of this section said it was. The collector builds `sub_objs` from `Acceptance._base_manager`,
and `base_manager_name` is unset, so that is a plain `Manager` producing a plain `QuerySet` — not
`AcceptanceQuerySet`, and therefore a queryset with no `update()` override to reach. Measured on
Django 5.2.17, each condition alone is harmless:

| `lazy_sub_objs` on the callable | `base_manager_name` → `AcceptanceManager` | Removing an account |
|---|---|---|
| absent | unset | succeeds — this is the shipped state |
| present | unset | succeeds; record survives, user cleared |
| absent | set | succeeds |
| present | set | refused with the guard's error |

So the attribute is left off because it buys nothing here, rather than because adding it breaks the
default. What a later change has to avoid is recreating the pair: the attribute puts the update on
the queryset path, and `base_manager_name` is what makes that queryset the guarded one.

## R2 — Enforcing "never changed" on a row where nothing may change

FS-001 had to freeze five of a version's six fields and leave `status` writable, so its guard
compares the stored row field by field. An acceptance has no equivalent: FR-004 freezes the whole
row, and FR-006 removes deletion as well. The guard is therefore simpler rather than more
complicated — an update to an existing acceptance is refused whatever it names.

The four routes are the same four FS-001 found, and the reasoning there (`001-legal-documents-kept/research.md`
R2) carries over unchanged:

| Route | Guard |
|---|---|
| `Acceptance.save()` on an existing row | Refuse. A row that already exists in the database is finished |
| `AcceptanceQuerySet.update()` | Refuse whenever the queryset matches anything |
| `Acceptance.delete()` | Refuse |
| `AcceptanceQuerySet.delete()` | Refuse |

`bulk_update()` needs no override for the same reason it needed none in FS-001: it calls
`self.filter(pk__in=pks).update(**update_kwargs)` internally, so the `update()` guard already stands
in front of it. It still gets a test, because that is a claim about Django's internals rather than
about this package.

`AcceptanceManager.use_in_migrations` covers the historical model a shipped migration would see,
which is the route FR-004 names explicitly.

**The one route that must stay open is the one R1 opens.** When a project has configured removal,
the account's deletion has to take the acceptances with it — and it does, without our guard being in
the way, because the collector does not call `QuerySet.delete()`. It issues the delete itself
through `sql.DeleteQuery(model).delete_batch(...)` or `qs._raw_delete(...)`
(`db/models/deletion.py:448`, `:467`, `:499-501`). So the package offers no operation that deletes an
acceptance, and the configured behaviour still works. The two requirements do not collide; they are
separated by which layer performs the delete.

Erasure on request (issue #22) will need a deliberate, audited route of its own, and it will have to
go around the guard the same way or be given an explicit key. That is its problem to design, not
this feature's to anticipate.

## R3 — One record per person per version, including under a race

FR-009 says a repeat leaves one record and does not fail; FR-010 says that holds when two attempts
arrive at once. Application-level "look, then write" cannot promise the second, so the constraint is
on the data: a unique constraint over the person and the version.

`get_or_create()` then gives the behaviour for free, and does so correctly under the race. It
attempts the `get`, falls through to a `create` inside `transaction.atomic()`, and on `IntegrityError`
re-runs the `get` and returns the row the other writer created (`db/models/query.py:938-960`). The
loser of the race gets the winner's record rather than an exception, which is exactly FR-009's
"succeeds and leaves them the one record they already had".

The `atomic()` block matters on PostgreSQL, where an `IntegrityError` poisons the surrounding
transaction unless the failing statement is in a savepoint of its own. Django puts it there. A
hand-rolled `try: create() except IntegrityError: get()` would not, and would break the caller's
transaction on the exact path it was written to handle.

## R4 — Answering "what is outstanding" without a query per document

FR-018 and SC-005 make this a correctness requirement rather than an optimisation: the answer has to
cost a fixed number of lookups, because R4's flow asks it on an ordinary page request.

The shape that does it is a single query with a subquery, not a loop over documents:

```python
accepted = Acceptance.objects.filter(subject=..., version__status=Version.Status.CURRENT)
Document.objects.filter(versions__status=Version.Status.CURRENT).exclude(
    pk__in=accepted.values("version__document_id")
)
```

One statement. Documents with nothing in force are excluded by the `filter`, which is FR-012's
second sentence and US-3 scenario 5. Documents whose in-force version this person has accepted are
excluded by the subquery. A person who accepted a version that has since been superseded is *not*
excluded, because the subquery only counts acceptances of the version currently in force — which is
US-3 scenario 3 and the reason the filter names the status rather than the document.

The one-document question (FR-011) is the same queryset narrowed to one primary key, rather than a
second implementation of the rule. Two expressions of "outstanding" would drift, and the one that
drifted would be the one R4 relies on.

`django_assert_num_queries` is how the suite holds the bound, per Article X — a counted assertion
rather than wall-clock timing, so it stays honest on a loaded machine.

## R5 — What identifies a person once the account is gone

FR-014 is the requirement that makes the default in FR-013 worth having: a record that survives its
account and can no longer say whose it is documents nothing. The foreign key cannot carry it,
because under the default the foreign key is exactly what gets cleared.

Three candidates were considered.

**The account's login name or email address.** Rejected by an edge case the spec states outright: an
account removed and recreated under the same name is a different person, and inherits nothing. An
email address would silently reattach the old records to the new account, which is the worst
available failure — it is wrong, it looks right, and it is wrong about evidence.

**A random identifier minted per acceptance.** It survives, but it groups nothing: issue #21 has to
produce one person's records as a set and issue #22 has to erase them, and neither can find a set of
rows that share no value.

**The account's primary key, copied onto the record when it is written.** This is what the plan
uses. It is stable for the life of the account, a recreated account gets a new one, and it is the
value every one of this person's records already shares. Article XV asks that a field which could
re-identify a person is justified where it is defined, and this one is: it is the least that can be
held and still answer whose record this is.

Stored as text rather than as the user model's own key type, because a host project's primary key
may be an integer, a UUID or a string, and a package that guesses gets it wrong for somebody. The
cost is that it is not a foreign key and the database will not join on it, which is correct here —
the point of the column is that it outlives the row it refers to.

## R6 — Where a request came from, and why the package will not guess

FR-016 lets a project hold more than the three facts, and Article XV names an IP address as the
example. Reading one is a question with a wrong answer that looks right.

`request.META["REMOTE_ADDR"]` is the address the connection came from. Behind a proxy or a load
balancer that is the proxy, and the client's address is in `X-Forwarded-For` — which is a header,
which means the client can set it. A package that reads `X-Forwarded-For` when it is present is a
package whose evidence field can be filled in by the person the evidence is about.

Resolving that correctly needs knowledge this package does not have: how many proxies stand in
front, which of them are trusted, and whether the header can be spoofed past them. Django's own
position is the same — it removed `SECURE_PROXY_SSL_HEADER`-style guessing from this area precisely
because only the deployment knows. So this package reads `REMOTE_ADDR` and nothing else, and
documents that a project behind a proxy is responsible for making `REMOTE_ADDR` correct, which is
ordinary Django deployment advice and is solved by middleware the project chooses.

The field is nullable and stays empty when no request is supplied, which keeps the manager usable
from a management command or a shell without inventing a value.

## R7 — Prior art

`django-termsandconditions` is the package a project adopting this one is most likely to be leaving.
Its `UserTermsAndConditions` records a user, a terms object and a date, and it is the closest thing
to this feature in the ecosystem.

Two differences are deliberate rather than incidental.

It points at a *terms* object that carries both an identity and a version string, so the record and
the wording are the same row. That makes "which wording did they agree to" answerable only if the
row was never edited, and nothing stops it being edited. FS-001 split identity from wording for this
reason, and this feature points at the version.

It offers `delete()` on the record like any other model, and its own views use it. This package
refuses on every route it ships, because an acceptance that can be deleted by ordinary means is not
evidence. The one path that should remove records is issue #22, and it will be deliberate and
audited rather than incidental.

Importing an existing `django-termsandconditions` history is out of scope and is recorded as such in
`decisions.md`.
