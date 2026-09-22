# Decisions — 004 Producing everything held about one person's acceptances

Rationale too long to sit inside `spec.md`, and the record of every ambiguity resolved without
escalating it. Each entry names what was unclear, what was chosen, and why the choice is
defensible.

## D1 — One answer about a person, not a report about acceptances

**Ambiguous**: R3 asks for a person's *agreements* to be producible, which reads as a report about
acceptances. But R8 will hold cookie choices and R9 will show a person their own consent, and both
are answers about the same person. Either this feature is the package's one answer and those join
it, or it is the first of three.

**Chosen**: the package's one answer about a person, built now over acceptances because that is all
the package holds.

**Why defensible**: Sam's ruling, and it is the reading the constitution already implies. A site
fielding a request wants what is held about this person, not what is held about this person in each
of the package's subsystems. Three places to look is how a partial answer gets handed over by
accident, which Article XIV singles out as worse than no answer. The cost is one requirement's
worth of structure now (FR-017) against a surface that R8 would otherwise have to either duplicate
or retrofit onto, with real records already in it.

What this deliberately does not mean: no abstraction is built today for records that do not exist.
The requirement is that adding a kind of record does not change what the answer is, which is a
constraint on the design rather than a licence to build a plugin system for one caller.

## D2 — Producing an answer is a privileged act with a permission of its own

**Ambiguous**: R3 says nothing about who may produce the answer, and the obvious reading is that
anybody who can already reach the site's staff surfaces can.

**Chosen**: a permission of its own, held by nobody by default.

**Why defensible**: this is the one place in the package where one person's consent history is
assembled and handed over, which makes it the highest-value surface here by some distance. Reusing
whatever permission governs editing documents would give every compliance editor the ability to
pull any member of the public's record, which is a different job with different risk. Held by
nobody by default because a permission that arrives switched on is one nobody decided to grant.

Refusals reveal nothing about whether the named person has records (FR-013), because a refusal that
distinguishes the two turns the surface into a way of confirming that a given person uses the site.

## D3 — The wording travels with the answer, in full

**Ambiguous**: whether each entry carries the wording served or points at where it can be read.
Pointing keeps the answer small, which matters when somebody has a dozen acceptances of long
documents.

**Chosen**: in full.

**Why defensible**: the wording *is* the evidence, which is why FS-001 fixes it at publication and
Article XIII forbids producing it again later. A reference is a promise that something will still
be there and still say the same thing when somebody follows it, and the whole premise of this
package is that promises about text are worth less than the text. An answer handed to a regulator
that says "the wording is at this address" has answered nothing.

The size cost is real and accepted. An abridged answer is not evidence, so there is no version of
this that is both smaller and correct.

## D4 — Producing an answer leaves no trace

**Ambiguous**: erasure in issue #22 is audited, so producing could be read as needing the same. A
site may also want to evidence that it responded to a request within a deadline.

**Chosen**: no. Reading records does not record anything.

**Why defensible**: an audit trail exists to establish that something changed and who changed it,
and producing an answer changes nothing. Against the case for it, a log of who looked at whose data
is itself personal data about people who did not ask for it, retained indefinitely, which is
exactly what Article XV is pointed at. A site that needs to evidence its response to a request
needs a record of the request and the response, which is a process it runs rather than a gap in
this package.

Raised with Sam at the spec gate as a possible separate feature rather than folded in here, because
an access log over consent data is a real want and is not this feature.

## D5 — No hooks for the host project's own data

**Ambiguous**: the README and Article XIV both mention exposing hooks so a project can join its own
data to the view a person has of their consent, which could be read as belonging here.

**Chosen**: not here. The answer covers what this package holds, and says so.

**Why defensible**: the hooks are R11, aspirational, and gated behind v2 for a reason. Building
them now would mean this feature's correctness depends on host projects implementing something
correctly, and a host project that implements it badly produces an answer that looks complete and
is not. Article XIV names that as worse than no answer. The statement of coverage in FR-015 is the
honest version of the same thing at a hundredth of the cost.

## D6 — The answer's form is left to planning

**Ambiguous**: R3 says "a form a person can actually be shown", which could mean a page, a
downloadable file, or a command an operator runs.

**Chosen**: the specification fixes the properties and not the mechanism: it can be handed to
somebody, it carries the wording in full, it is the same twice, and it is reachable only with the
permission.

**Why defensible**: every one of those properties is testable and none of them depends on the
choice of mechanism, while the choice itself depends on things best decided with the data model in
front of you. Fixing it here would be specification drifting into planning, and the properties are
what a reviewer would check either way.

## D7 — The page is in the admin, on a proxy model that carries no table

**Ambiguous**: D6 left the mechanism to planning, and this package serves no address of its own —
`tests/test_app.py` asserts on main that `mvp_compliance.urls` does not exist. So there is nowhere
obvious for a page to go.

**Chosen**: the Django admin, hanging off `Disclosure`, a proxy of `Acceptance` with no fields.

**Why defensible**: the admin is the only staff surface this package has, and FS-002 already put
the authoring screens there, so this is the "somewhere they already work" the specification
assumes. A `ModelAdmin` needs a registered model, and the three real models are each wrong: the
page is about a person rather than a document or a version, and registering `Acceptance` itself
would hand everyone holding `view_acceptance` a changelist of every person's consent history —
the risk D2 exists to close, and the shape of R10, which this feature does not build.

A proxy gets its own content type, so it also gets its own permissions (verified by reading
Django 5.2.17's `create_permissions`, which resolves content types with
`for_concrete_models=False`). That is what makes `produce_disclosure` the act's permission rather
than a second meaning for one of `Acceptance`'s.

The alternative was a `urls.py` for host projects to include. It would add the first address this
package serves, contradict a test on main, and leave every consuming project responsible for
mounting it behind something.

## D8 — One route, and it is a GET

**Ambiguous**: an answer could be a page, a downloadable file, or both, and the request could be a
GET carrying the person in the query string or a POST carrying it in a form.

**Chosen**: one page, one GET, no download.

**Why defensible**: SC-003 asks for one permission test per route with none left untested, so every
extra route is real, permanent test surface. A page already carries the wording in full and can be
printed, which is what D3 was protecting. A POST would be the wrong verb for a read that changes
nothing, and it would make "produce it twice" a resubmission rather than a reload — FR-006 is
easier to trust when re-producing an answer is refreshing the page.

The cost, accepted: the identifier appears in the request line a server logs, as every admin object
address already does.

A management command was considered and rejected. It has no request and no signed-in user, so
there is nothing for FR-012 to refuse and no honest way to satisfy SC-003 for it.

## D9 — The answer holds sections, not a list of acceptances

**Ambiguous**: FR-017 requires a further kind of record to join without the answer's shape
changing, while D1 forbids building an abstraction today for records that do not exist. Those pull
in opposite directions and the line between them is a design choice.

**Chosen**: the answer is a subject and a tuple of sections; a section is a heading, its entries,
and the partial that renders them. Today exactly one section is built.

**Why defensible**: it is the literal content of FR-017 at close to no cost. An answer shaped
`{subject, acceptances}` changes shape the day cookie choices arrive, and so does every consumer
that walked it — the retrofit the requirement exists to prevent. What D1 forbids is a registry, a
hook or an entry point, and there is none: the function that builds the answer names each kind it
knows about, nothing can register into it, and FR-018 is the reason.

## D10 — A person is named by free text, resolved to a subject

**Ambiguous**: the obvious control is a picker over the site's accounts, and the specification's
own US-4 is about somebody who no longer has one.

**Chosen**: one free-text field, resolved in order: an account's login name, an account's email
address, then the text itself as the identifier the records carry.

**Why defensible**: a picker cannot express the case US-4 exists for. Falling through to the text
itself is the only way to ask about a person whose account is gone, and it makes a question about
somebody the package has never heard of land on FR-005's answer rather than an error. A second
field for the rare case would make the ordinary case worse.

The ambiguity is real and small — an account whose login name is another account's identifier
resolves as the account — so the answer reports the subject it was produced for, and a reader can
see which reading was taken.

## D11 — The answer carries no time of its own

**Ambiguous**: a printed answer handed to somebody normally says when it was produced, and FR-006
requires two productions with no change to the records to say the same thing.

**Chosen**: no produced-at stamp, anywhere.

**Why defensible**: a clock reading on the page makes FR-006 false by construction, and FR-006 is
the requirement that lets anybody trust the answer at all — an answer that differs between two
readings cannot be evidence of anything. Whoever hands an answer over knows when they produced it,
and a site that needs that recorded needs a record of the request and its response, which D4
already established is a process it runs rather than a gap in this package.

## D12 — The optional client address is part of the answer

**Ambiguous**: FR-003 names the document, the version and the moment. FS-003 lets a project also
record the address a request came from, off by default, and this specification is silent about it.

**Chosen**: where a record holds one, the answer carries it.

**Why defensible**: FR-001 is "everything it holds about them", and on a site that turned that
setting on the address is something it holds about them. Omitting it would be a partial answer
presented as a complete one, which Article XIV names as worse than no answer. Nothing reads the
setting at produce time — what governs the page is whether the record in front of it holds an
address, which is also what keeps records written before it was turned on looking exactly as they
did.

## D13 — The form field is named `subject`, even though it holds free text

**Ambiguous**: `resolve_subject()` (D10) turns free text — a login name, an email address, or an
identifier a removed account's records still carry — into the subject `produce()` reads. Nothing
in the spec or plan names the field the page exposes for typing that text in.

**Chosen**: `DisclosureForm.subject`, and the same name in the query string.

**Why defensible**: the glossary term this story is told to use throughout code, tests and
commits is `subject` (brief `glossary_terms`), and `resolve_subject(form.cleaned_data["subject"])`
in `changelist_view()` reads as what it does rather than needing a second name translated into the
first at the boundary. The field's own `label` (`_("Person")`) and `help_text` are what a reader
sees; the internal name is not user-facing text.

**Revisit if**: a future story adds a second free-text input this page reads (unlikely — D8 keeps
this to one field), where two fields both plausibly named "subject" would collide.

## D14 — Two pre-existing test modules were extended, and the guardrail flagged them

**Ambiguous**: the modification guard flags any change to a test file that existed at the story's
base, and US-3 changed `tests/test_admin.py` and `tests/test_records.py`.

**Chosen**: approved. Both changes are additions.

**Why defensible**: the whole diff of both files across that range is new classes, new methods, and
one import line each. No assertion in either file was weakened, relaxed, skipped or deleted —
checked by reading every removed line in the range, of which there are two, both imports. Article X
ties one source module to one test module, so a story that adds a route to the admin has nowhere
else to put its tests, and the alternative — a test module per story — is the thing that article
exists to prevent.

**Revisit if**: a flag ever covers a removed or altered assertion rather than an addition, which is
a different finding and not one to approve here.

## D15 — The coverage statement's exact wording, and the sweep's two lists

**Ambiguous**: FR-015 fixes what the statement must say and FR-016 fixes what it must not, but
neither fixes its wording, and T054/T055 ask for "the list of names" and "the same claims" without
naming them.

**Chosen**: `PersonalRecord.coverage` returns one sentence pair: "This covers what this package
holds about this person. The project may hold further records about them elsewhere that are not
included here." `FORBIDDEN_REGULATION_NAMES` (GDPR, CCPA, CPRA, HIPAA, PIPEDA, LGPD, "data
protection act", "privacy act", each spelled out too where it has one) and
`FORBIDDEN_COMPLETENESS_CLAIMS` (phrases built around "request in full" and "satisfies … request",
not bare "in full" — see below) live once in `tests/test_admin.py` and are imported into
`tests/test_records.py`'s documentation sweep, so a name only has to be listed once for both sweeps
to catch it.

**Why defensible**: the statement names no regulation, does not say "complete" or "in full", and
does not reassure — it states what the answer covers and stops, per Article XIV and the
conventions note on this story's own wording. Bare "in full" was tried first and rejected: it
false-positives on `docs/disclosure.md`'s own pre-existing "hands it over in full", which describes
wording being shown uncut, not a request being satisfied — a different claim the same three words
make. The narrower phrases keep that sentence green while still catching "satisfies your request in
full" if it appeared. Sharing the two lists between the catalog sweep and the documentation sweep
was the deciding point for keeping FR-016 and SC-007 enforced by one list rather than two lists
drifting apart, the same reasoning T049a/T049b already applied to the catalog itself.

**Revisit if**: a real string needs "in full" in a context this sweep would wrongly catch, at which
point the phrase list needs a narrower entry rather than dropping the check.

## Scope raised and left out

**An access log over consent data.** Whether a site can see who produced whose records, and when.
It came out of the question in D4, it is a genuine want for a site that has to demonstrate how it
handles requests, and it is covered by no roadmap item. Raised with Sam separately rather than
widened into this feature, which answers requests rather than governing who may ask.
