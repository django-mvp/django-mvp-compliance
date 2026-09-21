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

## D12 — proving the numbering collision needs bypassing `save()`, not calling it

**Decision**: `TestVersion::test_number_cannot_collide_within_a_document` forces the
collision with `Version.objects.bulk_create([Version(document=..., number=1, ...)])`
rather than constructing a second `Version` and calling `.save()` on it.

**Why**: `Version.save()` always overwrites `number` with `max+1` on insert (D2 — the
package assigns it, not the caller), so a second `save()` call would never collide; it
would just get the next number. `bulk_create()` inserts rows without calling each
instance's `save()`, which is the only route in this story that reaches the table with a
caller-supplied number still intact — and that is what exercises
`unique_version_number_per_document` rather than the `save()` logic.

**Revisit if**: a future story adds another write path that bypasses `save()` (a
management command, a bulk import) — that path needs the same collision test, because
`save()`'s auto-assignment cannot protect it.

## D13 — docs/models.md written even though it is not in the brief's file scope

**Decision**: added `docs/models.md`, documenting `Document` and `Version`, though the
brief's scope list names only `mvp_compliance/models.py`, `mvp_compliance/migrations/`,
and the listed test files.

**Why**: the full verify's `docs` step (run once, at the end, per the implementer
protocol) failed on `docs-undocumented`: two new public names with no page describing
them. The protocol is explicit that new public surface with no page at all is a page
written in the story it belongs to, unless the brief says otherwise — the brief is
silent on documentation, not opposed to it, and the gate is red without the page.

**Revisit if**: a later story finds `docs/models.md` a better fit merged into a larger
page (e.g. once publishing and rendering land) — nothing here is meant to be the final
shape of the package's documentation.

## D14 — `Version`'s partial constraints match `Status` values as string literals, not the enum

**Decision**: `one_current_version_per_document` and `version_status_agrees_with_published_at`
write `status="draft"` / `status="current"` directly rather than `Status.DRAFT` /
`Status.CURRENT`.

**Why**: both constraints are declared inside `Version.Meta`, a nested class. A nested class's
body does not see names bound in its enclosing class's body — that scoping rule is Python's, not
Django's — so `Status` (bound in `Version`'s body, one level up) is not a name `Meta`'s body can
resolve; referencing it raises `NameError` at class-definition time. The values are stable
(`Status` is this story's own new enum, not sourced from elsewhere), so the literal is written
once, at the point Python's scoping forces it, rather than routed around with a forward-reference
trick.

**Revisit if**: a `Status` value's string ever changes — both constraints need updating by hand,
since nothing ties them to the enum.

## D15 — `publish()` does not translate a constraint `IntegrityError` into `PublishError`

**Decision**: `plan.md`'s Publishing section describes an `IntegrityError` from the partial
unique index being translated into `PublishError` inside `publish()`. This story does not build
that translation.

**Why**: no task's acceptance criteria in `US2-brief.json` exercises it, and on every backend the
row lock `publish()` takes serialises the ordinary path before the index is ever reached — the
index only fires on a route that bypasses `publish()` entirely (T025's own test does exactly
that, directly, not through `publish()`). Adding a catch clause with no test behind it is the
kind of untested capability `craft-increments` asks not to build.

**Revisit if**: a later story finds a real path that reaches the constraint through `publish()`
itself (for instance, a host project running without the row lock's guarantee) — then the
translation earns a test and belongs with it.

## D16 — `use_in_migrations = True` landed with T031, not T032

**Decision**: `VersionManager.use_in_migrations = True` was written as part of T031's commit,
alongside the manager and queryset it belongs to, rather than held back for T032 as `tasks.md`
lists it. T032's own commit is the test alone, and it is green from the moment it is written.

**Why**: the attribute is one line on the same class T031 was already introducing; splitting a
single class definition across two commits to keep the red/green boundary exactly on the task
line would have meant an incomplete `VersionManager` sitting in the tree between T031 and T032,
which is a worse state than the test arriving already green.

**What the tests cover**: `test_historical_version_model_uses_this_packages_manager` reads the
manager off migration state, and migration `0004` records it there permanently. Take
`use_in_migrations` off the class and that test stays green. Only `makemigrations --check` goes
red, because the autodetector then wants the manager taken back out of state. The declaration
therefore gets its own assertion on the class,
`test_the_manager_is_declared_for_use_in_migrations`, confirmed red with the attribute removed
and green with it restored. The two tests answer different questions: one that the declaration
is there, one that a historical model ends up holding the manager.

**Revisit if**: a later story's task split assumes T032 introduces new model behaviour rather
than only the test for it.

## D17 — the US-3 guardrail flag on `tests/test_models.py` is an import block, not a weakened test

**Decision**: the guardrail scan over US-3's commits flags `tests/test_models.py` as a modified
pre-existing test file. Accepted as clean.

**Why**: the flag is raised per file, and every removed line in the range is an import line that
US-3 rewrote to bring in `connection`, `transaction`, `MigrationLoader`, `ProtectedError`,
`PublishedVersionError`, `VersionManager` and `DocumentFactory`. All eighteen test functions
present before US-3 are present afterwards, byte-for-byte, and US-3 only appends a new
`TestImmutability` class below them.

**Revisit if**: a later story's flag on the same file covers a range where a test body, and not
only the import block, differs.

## D18 — `TestMarkdownRenderer` (T040) and `TestRendererSetting` (T043) were written together, in one file, one commit

**Decision**: both test classes for `tests/test_rendering.py` were authored in T040's commit,
even though the brief assigns `TestMarkdownRenderer` to T040 and `TestRendererSetting` to T043.
`TestMarkdownRenderer` could not be run standalone between T040 and T043: the single `from
mvp_compliance.rendering import MarkdownRenderer, get_renderer` import line fails to collect the
whole module until `get_renderer` exists, exactly as `tests/test_models.py` importing both
`Document` and `Version` would if either were missing.

**Why**: the brief itself places both test classes in the same file, so the coupling is inherent
to the task split, not introduced by how the tests were written. T042 (`MarkdownRenderer`) was
verified instead by a manual script running every assertion in `TestMarkdownRenderer` directly
against `MarkdownRenderer().render()` — recorded in `progress.md`'s T042 entry — rather than by
a `pytest` run, since no `pytest` run of that test could succeed in isolation at that point. This
mirrors T041/T042's own documented reason for landing adjacent tasks that are not independently
green: `pyproject.toml`'s dependency declarations for `markdown` and `nh3` fail `deptry` until
`rendering.py` imports them, by the brief's own design.

**Revisit if**: a later story's brief splits two tests across two files instead of one, or a task
brief separates a class and its dependency into non-adjacent tasks — either removes the coupling
this decision is about.

## D19 — `nh3.clean()` is called with `link_rel=None`

**Decision**: `MarkdownRenderer.render()` passes `link_rel=None` to `nh3.clean()`.

**Why**: `nh3.clean()`'s default `link_rel="noopener noreferrer"` adds a `rel` attribute to every
`<a>` tag regardless of the `attributes` argument passed in. plan.md's Rendering section declares
`allowed_attributes` as an explicit set including `{"a": {"href", "title"}}` and nothing about
`rel`; T040's test asserts a link renders as exactly `<a href="https://example.com">a link</a>`.
Without `link_rel=None`, that assertion failed on the first run with an unexpected `rel="noopener
noreferrer"` on the tag — not a bug in the test or the allow list, but `nh3` adding an attribute
outside the ones this renderer declares.

**What makes it safe**: `rel="noopener noreferrer"` protects a link that opens a new browsing
context, and `target` is not an attribute this renderer allows, so a rendered link cannot open
one. That is the whole of the argument, and it holds only as long as `target` stays out of the
allow list — so `test_a_link_cannot_open_a_new_browsing_context` asserts it, confirmed failing
with `target` added and passing with it removed.

**Revisit if**: a later story wants `rel` on rendered links (for instance, `noopener` on links a
reader might open from published content) — set `link_rel` explicitly rather than relying on
`nh3`'s default, and add it to `allowed_attributes` so the allow list stays the single source of
truth for what a tag may carry.

## D20 — migration `0005` was generated at T044, committed at T048

**Decision**: `poetry run python manage.py makemigrations mvp_compliance` was run once, during
T044, to generate `mvp_compliance/migrations/0005_...py` — without it, the `html` column doesn't
exist in the test database and T044's own tests can't run. The generated file was left uncommitted
(and therefore untracked, not staged) through T045–T047, and committed only at T048, under that
task's own commit.

**Why**: T045 (the empty-output refusal) and T047 (`html` joining `PUBLISHED_FROZEN_FIELDS`) are
both pure Python behaviour changes — neither touches a model field or constraint, so neither needed
a new migration, and running `makemigrations` again at T048 produced "No changes detected",
confirming the file generated at T044 already covered the whole story's schema change. Generating
the migration early (to make T044 verifiable at all) and committing it late (to keep the migration
task, T048, meaningful as its own commit with its own acceptance check —
`makemigrations --check --dry-run` clean — rather than an empty no-op) keeps both the brief's task
boundaries and the tree's actual runnability intact.

**Revisit if**: a later story in this feature adds a task between a model-changing task and its
migration task that itself changes the model — the deferred-commit approach only holds because
nothing did here.

## D21 — `VersionManager` forwards `published()`/`drafts()`/`current()` explicitly, rather than being built with `Manager.from_queryset()`

**Decision**: `VersionManager` keeps its existing `get_queryset()` override and gains three thin
methods — `published()`, `drafts()`, `current()` — each returning `self.get_queryset().<method>()`.
`Manager.from_queryset(VersionQuerySet)` was tried first and rejected.

**Why**: a bare `get_queryset()` override does not forward a queryset's own methods onto the
manager, and `document.versions` is a related manager built from `VersionManager`, so
`document.versions.published()` raised `AttributeError: 'RelatedManager' object has no attribute
'published'` before this change (T050, observed). `Manager.from_queryset(VersionQuerySet)` as
`VersionManager`'s base class does forward the methods, but mypy refuses it outright:

```
mvp_compliance/models.py:89: error: Unsupported dynamic base class "models.Manager.from_queryset"  [misc]
Found 1 error in 1 file (checked 5 source files)
```

`from_queryset()` builds its return value at runtime, so mypy has no static class to check against
— there is no type annotation that makes this pass; the base class itself is what is rejected.
Silencing it with `# type: ignore[misc]` was available but not taken: it would suppress mypy's
view of every method the manager gains this way, not just this one dynamic base, which is a wider
loss of type-checking than three named methods cost to write out.

**What makes it safe**: each forwarding method is a one-line delegation with its own return type
annotation (`VersionQuerySet`), so mypy checks the manager's public surface the same way it checks
everything else in this file — confirmed clean, `Success: no issues found in 5 source files`. T050
covers all three routes: `document.versions.published()`, and the current-version query that
`Document.current` sits on top of.

**Revisit if**: `VersionQuerySet` gains a fourth method a related manager needs to expose — add the
same one-line forward rather than switching to `from_queryset()`, since the mypy rejection is
structural to that API and does not change with the method count.
