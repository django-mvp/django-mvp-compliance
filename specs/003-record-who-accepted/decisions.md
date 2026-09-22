# Decisions — 003 The record of who accepted which version

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — Acceptances survive a removed account by default, and a setting says otherwise

**Ambiguous**: an account being closed or tidied up is not an erasure request, but Django's
ordinary behaviour when an account goes is that things attached to it go with it. Two readings are
defensible. Keeping the records honours Article XII, which says an acceptance is never deleted.
Removing them honours Article XV, because a closed account otherwise leaves personal data behind
indefinitely with nobody watching it.

**Chosen**: a setting the host project controls, defaulting to the records surviving.

**Why defensible**: Sam's ruling that a genuinely two-sided question becomes a setting rather than a
guess. The default is the package's own position, which is that evidence outlives convenience: a
site facing a dispute about what somebody agreed to in 2029 is not helped by a record that vanished
when an administrator tidied up an account in 2027, and losing it as a side effect of an unrelated
action is precisely the failure this package exists to prevent. A site that means the opposite sets
the option and gets it, and a site that wants one person's records gone has the deliberate path in
issue #22.

The cost is named rather than hidden: under the default, closing an account does not remove what is
held about that person here, and a project that assumed it did would be wrong. That belongs in the
documentation this feature ships, not only in a setting's docstring.

## D2 — An acceptance can name any published version, not only the one in force

**Ambiguous**: whether the record may point at a superseded version. The obvious reading is that
people accept what is in force, so anything else is a mistake to be refused.

**Chosen**: any published version. Drafts are refused.

**Why defensible**: the race is real rather than theoretical. A person opens the document, reads
it, and a new version is published before they submit. Refusing their acceptance either throws away
something that happened or, worse, records them against wording they never read. Recording what
they actually saw is the only answer consistent with Article XIII, where the stored output is the
evidence. The safety property is preserved elsewhere: what a person has *outstanding* is measured
against the version in force, so that person is simply asked again, which is the correct outcome.

Drafts are refused because a draft has no legal standing at all and accepting one would create a
record pointing at something that can still be edited.

## D3 — Accepting the same version twice leaves one record and does not fail

**Ambiguous**: append-only could be read as meaning every submission produces a row, which would
make a double-submitted form produce two identical records. The alternative reading, that it is an
error, would fail a person who did nothing wrong.

**Chosen**: at most one acceptance per person per version. A repeat succeeds and leaves the record
that already exists.

**Why defensible**: append-only is about facts, not about submissions. Someone clicking twice has
agreed once, so two records would misrepresent what happened as much as an overwrite would. Failing
would push the problem into the flow in R4, where a person meeting an error after agreeing has no
idea whether it worked. Concurrency matters here: two simultaneous submissions have to end at one
record, which is a constraint on the data rather than a check the calling code performs.

## D4 — The outstanding question is answered for every document, and R5 filters it

**Ambiguous**: whether "what does this person have outstanding" should already exclude documents a
site does not enforce. A cookie policy is normally published and never enforced, so including it
looks like a bug.

**Chosen**: this feature answers for every document with a version in force. Enforcement filtering
belongs to R5.

**Why defensible**: enforcement is a policy, and a policy baked into the record layer is a policy
that cannot be changed without touching evidence handling. The account page in R9 and the site-wide
picture in R10 both want the unfiltered answer, so filtering here would force two of the three
consumers to work around it. R5 owns the per-document enforcement decision and applies it to the
answer this feature gives.

## D5 — A surviving record still has to name its person

**Ambiguous**: "the records survive" is only half a statement. A record whose account is gone and
which can no longer say who it belonged to is not evidence, and the two features that read it,
issues #21 and #22, both need to find one person's records as a set.

**Chosen**: a requirement that a surviving record continues to identify the person and continues to
be retrievable with that person's other records. How that identity is held is left to the
implementation.

**Why defensible**: this is the difference between the setting doing what it says and appearing to.
It is a property of the record rather than a design, so it belongs in the specification, while the
mechanism is exactly the kind of decision that should be made with the data model in front of you.
Article XV bears on it directly, because whatever is held for this purpose is personal data that
outlives the account, and it has to be justified where it is defined.

## D6 — Configured removal carries no audit trail, and erasure on request is a separate problem

**Ambiguous**: R3 asks for erasure to be auditable. The setting in D1 also removes records, so it
could be read as needing the same trace.

**Chosen**: no. The setting is a standing behaviour a project configured, not an act about a named
person.

**Why defensible**: an audit trail answers "who decided this, about whom, and when". For a
configured behaviour the answer is the same for everybody and is already recorded in the project's
own configuration history. Erasure on request is the opposite: one person asked, somebody acted,
and that is worth a trace. Designing that trace is issue #22's work, including the question of what
a record of an erasure may itself hold about the person who asked for it.

## Scope raised and left out

**Bringing in acceptances from a previous system.** A site adopting this package usually has
acceptance history already, most often from `django-termsandconditions`. Those are facts that
happened, and appending them breaks no rule here. It is covered by no roadmap item, and it was
raised at intake as a possible gap rather than folded into this feature, because importing records
whose original wording may not be available raises questions this specification does not answer.

---

*Entries below were settled at planning, after the specification merged. Each one is an ambiguity
the specification deliberately left to the design.*

## D7 — The person is held twice: a foreign key and a copied identifier

**Ambiguous**: D5 requires a surviving record to still name its person and to still be findable with
that person's others, and leaves the mechanism open. A foreign key alone cannot do it, because under
the default in D1 the foreign key is precisely what gets cleared.

**Chosen**: a nullable foreign key to the host project's user model for the ordinary relationship,
plus a `subject` column holding that account's primary key as text, written when the record is.

**Why defensible**: the two alternatives both fail on a stated requirement. An email address or login
name reattaches a person's old records to a recreated account with the same name, which the spec's
own edge case says must not happen — and it fails by looking correct. A random per-record identifier
survives but groups nothing, so issue #21 could not produce a person's records as a set and issue #22
could not erase them. The account's primary key is stable for the life of the account, is new for a
recreated one, and is already shared by every record belonging to that person. Article XV is
satisfied by it being the least that can be held and still answer whose record this is, and the
justification sits in the field's own `help_text`.

The cost is one denormalised column that the database will not join on. That is the point: a foreign
key is a pointer to a row that may be gone, and this column has to outlive it.

## D8 — A callable `on_delete`, not a signal receiver

**Ambiguous**: FR-013 asks for a setting deciding what happens to acceptances when an account is
removed, and `on_delete` is fixed when the model class is built. The obvious workaround is a
`post_delete` or `pre_delete` receiver that removes the records when the setting says so.

**Chosen**: a callable in the `on_delete` position that reads the setting when the delete runs.

**Why defensible**: `on_delete` takes any callable with the collector's signature — that is all
Django's own `CASCADE` and `SET_NULL` are — so the setting can be read at deletion time rather than
at import time, which is what makes it a setting a project can change. A signal instead would mean
two mechanisms deciding one thing, running in an order nothing guarantees, and it would be skipped by
the bulk deletion paths an administrator tidying up accounts is most likely to use. One decision,
one mechanism, on the path every delete already goes through.

## D9 — `accepted_at` is a value the record carries, not a write behaviour

**Ambiguous**: `auto_now_add=True` is the ordinary Django idiom for "when this happened" and is
shorter than setting the field.

**Chosen**: the recording method sets `accepted_at`.

**Why defensible**: `auto_now_add` makes the field a property of the write rather than of the fact,
and it rewrites on every save — the exact behaviour Article XII forbids for a row that is finished
the moment it exists. Setting it once, where the fact is recorded, also means the one field that says
*when* can be supplied by a caller importing history it already holds, should issue #22's neighbour
ever be built.

## D10 — The package reads `REMOTE_ADDR` and will not parse a forwarded header

**Ambiguous**: FR-016's additional evidence means the address a request came from, and behind a proxy
`REMOTE_ADDR` is the proxy rather than the person.

**Chosen**: read `request.META["REMOTE_ADDR"]` only. A project behind a proxy is responsible for
making that value correct.

**Why defensible**: `X-Forwarded-For` is a header, so the client can set it. A package that reads it
when present has an evidence field that the person the evidence is about can fill in, which is worse
than holding nothing. Resolving it correctly needs facts only the deployment has — how many proxies
stand in front, and which of them are trusted — so this is a case where the package genuinely cannot
know and must not guess. Making `REMOTE_ADDR` correct is ordinary Django deployment work with
well-understood middleware, and it is where the knowledge lives.

## D11 — One expression of "outstanding", narrowed for the single-document question

**Ambiguous**: FR-011 asks about one document and FR-012 about all of them, which reads like two
methods.

**Chosen**: one queryset answering FR-012, and the single-document answer is that queryset narrowed
to one primary key.

**Why defensible**: two implementations of one rule drift, and the one that drifts is the one the
flow in R4 calls on every page request. The narrowing costs a `filter(pk=...)` and an `exists()`, both
of which the database was going to do anyway, and it means the query-count bound in SC-005 is proven
once for both answers.

## D12 — T015 landed before T014, not after

**Decision**: `mvp_compliance/exceptions.py`'s `RecordError` and `RecordedAcceptanceError` were
committed as T015 before `AcceptanceManager.record()` (T014), reversing the order `tasks.md` lists
them in.

**Why**: `record()`'s own acceptance criterion has it raising `RecordError` on a draft version, and
T012's test (committed earlier, as designed) already asserts `pytest.raises(RecordError)`. Written
in the order `tasks.md` lists, T014's commit would import a name `exceptions.py` does not yet
define — the module fails to import, not for the reason any test intends. Landing T015 first makes
every subsequent commit's failures, and eventual passes, about the behaviour each task claims.

**Revisit if**: a later story's task list assumes `tasks.md`'s T014/T015 order matches commit
order — it does not on this branch.

**ADR:** none — commit sequencing within one story, not a design change. Both tasks' own file scope
and acceptance criteria are exactly as `tasks.md` states.

## D13 — Six pre-existing test files were extended, and that is what the guardrail flagged

**Decision**: the guardrail that flags modifications to tests written before this branch raised six
flags — `tests/conftest.py`, `factories.py`, `test_exceptions.py`, `test_factories.py`,
`test_migrations.py` and `test_models.py`. All six are accepted.

**Why**: the repository's test layout ties one test module to one source module, so a second model
in `models.py` has nowhere to go but `tests/test_models.py`, and a second factory has nowhere to go
but `tests/factories.py`. Extending those files is the layout working as intended rather than a
sign of a test being worked around. The whole of what was removed across the six files is five
import lines and one module docstring sentence, each replaced by a wider version of itself; no
assertion was changed, weakened or deleted, and the suite grew from 65 tests to 83.
`tests/test_migrations.py` reads as the one that deserves a second look, and its diff is a docstring
and a comment — the assertion itself is untouched and now covers acceptances as well as versions.

**Revisit if**: a story ever needs to change what a pre-existing test asserts, rather than to add
beside it. That is a different act and does not belong in this entry.

**ADR:** none — a record of one triage decision on one branch, with nothing downstream inheriting it.

## D14 — T033 and T034 land red on their own commits, and T035 is what turns them green

**Decision**: `tests/test_models.py::TestRecording::test_a_second_row_is_refused_by_the_database`
(T033) and `::test_two_recordings_leave_one_record` (T034) both fail on the commit that introduces
them — not for a missing table this time, but because `one_acceptance_per_person_per_version` is on
`Acceptance.Meta` (T032) and not yet in the schema pytest-django builds the test database from. Both
turn green only once T035 generates the migration.

**Why**: `tasks.md` states T033's and T034's own "Done when" as "Passes", which their own commits do
not satisfy — but a constraint's `AddConstraint` migration is what makes SQLite enforce it, and
`Meta.constraints` alone does not (confirmed by probe: `bulk_create()`-ing a duplicate row after
T032 but before T035 raised nothing). Generating a migration per model-touching task, rather than
once at the story's model-work boundary, was rejected as the alternative: T021 already established
the pattern of landing several red, table-shaped tests across T010–T020 and turning them green
together at the one migration task, and re-deriving a fresh migration after every field or
constraint would produce several migrations this story squashes at convergence anyway (T070) for no
benefit before then. T033 and T034 follow the same sequencing T021 set, for the same reason.

**Revisit if**: a future story's migration task is skipped or reordered on the assumption that every
task before it must independently pass — on this branch, model-shape tasks are allowed to stay red
until the migration task lands, and `forge check-receipts`/tamper-check should read a red
intermediate commit as expected rather than as a guardrail trip, the same way it already does for
T010–T020.

**ADR:** none — commit sequencing within one story, matching D12 and the precedent T021 already set.

## D15 — SC-002's third version was added at acceptance, not left as a noted gap

**Decision**: `test_accepting_a_later_version_of_the_same_document_creates_a_second_record` now
records three successive versions and asserts the first two are untouched, rather than two versions
with only the first checked.

**Why**: SC-002 states the outcome in terms of three successive versions and the first two being
exactly what they were when written. The story's own report raised the shortfall as a concern and
argued the mechanism — per-row uniqueness plus `Meta.ordering` — has no version-count-dependent
behaviour, which is true and is why nothing was broken. It is still the wrong test to leave behind:
a criterion that names a cardinality should be read back by a test that reproduces it, so the test
fails if anyone later introduces a behaviour that only shows up past the second record. The cost was
six lines.

**Revisit if**: never as stated — but the general rule is worth keeping, that a success criterion
naming a specific count is reproduced at that count rather than at the smallest count that exercises
the same branch.

**ADR:** none — a test brought up to the criterion it already cited.

## D16 — Main was integrated mid-feature, because the pull request was running no checks at all

**Decision**: `origin/main` was merged into this branch after US-3 rather than at convergence, and
the conflicts were resolved as described below.

**Why**: the authoring and publishing feature merged to main while this branch was being built, and
the two branches touched the same five files. A conflicted pull request has no merge commit for
GitHub to build, so no `pull_request` workflow runs at all — the branch was not failing its checks,
it had stopped having any. Every green check on the pull request predated the whole of this feature's
code. Waiting until convergence would have meant three more stories with no continuous integration
and a larger conflict to resolve at the point where the margin for error is smallest.

**What the resolution decided**:

- **Both branches added a `UserFactory`.** Main's is kept and this branch's is dropped. Main's
  carries an email, staff and superuser flags and a usable password, which the admin tests need and
  which nothing here is harmed by. Two factories for one model is what the testing standard exists
  to prevent. This branch's `test_two_builds_do_not_collide` is therefore gone, replaced by main's
  `test_two_builds_do_not_collide_on_username`, which asserts the same thing under the name the
  sibling factories already use. T001's evidence in `feature-state.json` names the old test, which
  no longer exists.
- **Both branches took migration `0002`.** This branch's two migrations are renumbered to `0003` and
  `0004` and now depend on main's `0002_version_publish_permission`, because two leaf nodes on one
  app is a state Django refuses to migrate at all. T070's squash target moves to `0003_*`
  accordingly.
- **The catalogue had to be regenerated now rather than at T071.** Main added a test that every
  translatable string this package ships appears in the shipped catalogue, and this feature's
  strings did not. Regenerating it turned up exactly the failure the catalogue's own header warns
  about: the entry for "An acceptance cannot be deleted." was marked fuzzy and given "A published
  version cannot be deleted." as its text. It is corrected.
- **The README's claim that the package registers nothing in the admin is deleted**, because main
  made it false.

**Revisit if**: nothing here. The general point worth keeping is that a conflicted pull request
reads as quiet rather than broken, so "no failing checks" and "checks passing" have to be told apart
by looking.

**ADR:** none — a record of one integration on one branch.

## D17 — The stated reason for leaving `lazy_sub_objs` off the callable was wrong, and is corrected

**Decision**: `research.md` R1, `plan.md`, `tasks.md` T052 and the callable's own docstring said that
giving `keep_or_remove_acceptances` a `lazy_sub_objs` attribute would route the field update into
`AcceptanceQuerySet.update()` and turn every account removal under the default into an unhandled
refusal. It would not. All four now say what actually happens, and a test pins it.

**Why**: measured on Django 5.2.17 rather than reasoned from the deletion module. The collector
builds `sub_objs` from `Acceptance._base_manager`, and `base_manager_name` is unset, so that is a
plain manager and a plain queryset with no `update()` override to reach. Adding the attribute by hand
leaves account removal working exactly as it does without it — the record survives, its user is
cleared, nothing is raised. The refusal appears only when the attribute is present *and*
`base_manager_name` names `AcceptanceManager`, putting the guarded queryset in the collector's path.
Either alone is inert.

The original reading was right about the routing and wrong about the destination, which is an easy
mistake to make from the deletion module alone: the branch at `deletion.py:476-490` genuinely does
choose between `combined_updates.update(...)` and a raw `UpdateQuery`, but which queryset class
`combined_updates` belongs to is settled somewhere else entirely.

**What changed as a result**: the prohibition stands, because the attribute buys nothing here, but it
is no longer stated as a load-bearing safety property. `TestAccountRemoval::test_the_collector_does_
not_update_through_the_guarded_queryset` asserts both halves of the pair, and was checked against the
defect — reintroducing the attribute fails it.

**Revisit if**: `Meta.base_manager_name` is ever set on `Acceptance`. That is the change that makes
the other half matter.

**ADR:** none — a correction to this feature's own research, with nothing outside it affected.
