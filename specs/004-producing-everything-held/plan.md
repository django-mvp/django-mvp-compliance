# Implementation Plan: Producing everything held about one person's acceptances

**Branch**: `004-producing-everything-held` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-producing-everything-held/spec.md`

## Summary

One function, one page, one permission. Nothing is stored.

`mvp_compliance.records.produce(subject)` reads the acceptances held under one subject identifier
and returns a frozen `PersonalRecord`: the subject it was produced for, a statement of what it
covers, and a tuple of sections. A section is one kind of record the package holds — today there is
exactly one, acceptances — and each of its entries names the document, the version number, the
moment, and the wording served, read from the HTML publication stored rather than produced again.
One query, whatever the number of documents. No clock is read, so producing twice gives the same
answer.

The page is in the Django admin, because that is the only staff surface this package has and the
package serves no address of its own. It hangs off `Disclosure`, a proxy of `Acceptance` that
carries no table and exists so the act has a name in the admin index, an address, and a permission
of its own. The permission is `mvp_compliance.produce_disclosure`, held by nobody by default, and
it is the only thing the page's every permission hook consults — holding every other permission
this package defines, including the proxy's own routine `view_disclosure`, reaches nothing.

The person is named by one free-text field, resolved to a subject: an account's login name, an
account's email address, or — for somebody whose account is gone — the identifier their records
still carry.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.14)

**Primary Dependencies**: Django 5.2 and 6.0, django-mvp. **No new runtime dependency** — a
dataclass, a proxy model, a `ModelAdmin`, a form and two templates, all of them Django.

**Storage**: none. One migration (`0004_disclosure.py`) creating a proxy model and its permission;
no table, no column, no data.

**Testing**: pytest with pytest-django, `tests/settings.py`, an in-memory SQLite database.
`factory_boy` factories per Article X, `django_assert_num_queries` for the bound in SC-008, and the
`client` fixture against real users for every route assertion — a `ModelAdmin` method called
directly proves nothing about what a request receives.

**Target Platform**: a Django project that has installed django-mvp.

**Project Type**: installable Django application. This feature has a surface a person sees, so it
is walked through on the demo project before the merge gate.

**Constraints**: Article XIII (the stored output is the evidence; never re-render), Article XIV (the
answer states what it covers and names no regulation), Article XV (nothing new is stored, and the
one optional field FS-003 holds is disclosed rather than hidden), Article II/III (no registry, no
hook, no settings object for a feature with no settings).

**Scale/Scope**: one module of dataclasses and one function, one proxy model, one `ModelAdmin`, one
form, two templates, five user stories, 18 functional requirements, no new stored data.

## Constitution Check

Read before planning and re-checked after the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every requirement is an assertion about what an answer contains or who may produce it. SC-003 makes one test per route mandatory, and the failing test comes first on every task | Pass |
| II Simplicity | One function, one page, one permission. No export format, no report model, no service layer, no setting | Pass |
| III Anti-Abstraction | The section shape is the literal content of FR-017 and stops there: no registry, no hook, no entry point, and the builder names the one kind it knows | Pass |
| IV Integration-First | The contract is the `PersonalRecord` R8 and R9 will extend and read, and every acceptance scenario exercises it the way they will | Pass |
| V Security & data-safety | The feature's whole third story. One route, gated before any lookup, so a refusal is identical whether or not the person has records. The wording is served from the HTML sanitised at publication, never re-rendered | Pass |
| VI Documentation | `docs/disclosure.md` is new and linked from the README; `docs/models.md` gains the produced answer; the CHANGELOG gains an Added entry naming the page and the permission | Pass |
| VII Dependency discipline | No new runtime dependency | Pass |
| VIII Internationalization | Every `verbose_name`, `help_text`, form label, page string and statement of coverage wrapped with `gettext_lazy` or `{% translate %}`; the shipped `en` catalog regenerated. `tests/test_admin.py::TestUserFacingStrings` sweeps it automatically | Pass |
| IX Data-model conventions | The proxy adds no field. Its `Meta` carries `verbose_name`, `verbose_name_plural` and the one permission, each explained where it is declared | Pass |
| X Test structure & fixtures | `tests/test_records.py` is new and mirrors `mvp_compliance/records.py`; `tests/test_admin.py` grows a class for the page. One factory per model — the proxy gets none, because it builds nothing | Pass |
| XI Cohesion (Python) | Building the answer is module-level functions over frozen dataclasses, because it holds no state and belongs to no row. The route, its permission hooks and its rendering are the `ModelAdmin`'s | Pass |
| XII Published version immutable, record append-only | Nothing here writes. The page offers no add, change or delete, and its admin hooks return `False` for all three rather than relying on the model's refusals | Pass |
| XIII Rendered output is the evidence | The reason US-2 exists. Each entry carries `version.html` as stored at publication; the renderer is never called | Pass |
| XIV Mechanics, never compliance | US-5 is this article applied at the one point the package's output is handed to a member of the public. The answer states what it covers, and no string or documentation page names a regulation | Pass |
| XV Personal data minimal | Nothing new is stored, and producing leaves no trace — no access log, which would be personal data about people who did not ask for it (`decisions.md` D4) | Pass |
| XVI Compatibility | Pre-1.0. One proxy model, no existing model changes shape, no record is carried forward or at risk | Pass |

## Project Structure

### Documentation (this feature)

```text
specs/004-producing-everything-held/
├── spec.md              # on main, merged in #38
├── decisions.md         # on main; appended to, never restarted
├── plan.md              # this file
├── research.md          # the eight questions the design rests on
├── tasks.md             # the task list feature-state.json tracks
├── progress.md          # the running log
└── feature-state.json   # the ledger
```

No `data-model.md` and no `contracts/`: this feature stores nothing, and its contract is a Python
surface with no wire format to specify.

### Source code

```text
mvp_compliance/
├── records.py           # new: AcceptanceEntry, Section, PersonalRecord, produce(), resolve_subject()
├── models.py            # + Disclosure (proxy of Acceptance, no table)
├── admin.py             # + DisclosureAdmin
├── forms.py             # + DisclosureForm
├── migrations/
│   └── 0004_disclosure.py
├── templates/admin/mvp_compliance/disclosure/
│   ├── produce.html     # the page: the field, and the answer when one was asked for
│   └── acceptances.html # the acceptances section's entries
└── locale/en/LC_MESSAGES/django.po   # regenerated

tests/
├── conftest.py          # + a fixture for somebody holding the permission, and one holding
│                        #   every other permission this package defines
├── test_records.py      # new: TestProduce, TestWording, TestSurvivingRecords, TestCoverage
├── test_admin.py        # + TestDisclosurePage, TestDisclosureRefusals
└── test_app.py          # + the proxy is registered and Acceptance itself is not

docs/disclosure.md       # new: the page, the permission, and what the answer covers
docs/models.md           # + the produced answer
README.md                # + the page, and a link to docs/disclosure.md
CHANGELOG.md             # + the Added entry
```

**Structure Decision**: `records.py` is a new module rather than more of `models.py`. Article XI
puts behaviour with the state it belongs to, and this behaviour belongs to no row: it reads three
models and returns frozen values that are not models at all. Article X then gives it
`tests/test_records.py`, mirroring it.

## Design

### The answer

Three frozen dataclasses in `mvp_compliance/records.py`, none of them a model:

**`AcceptanceEntry`** — one acceptance, as it appears in the answer.

| Field | Type | Why |
|---|---|---|
| `document` | `str` | FR-003. The document's name as it stands now — the name is the document's lasting identity and is not versioned |
| `version` | `int` | FR-003. `Version.number`, which the package assigns |
| `accepted_at` | `datetime` | FR-003 |
| `wording` | `str` | FR-007, FR-008, FR-009. `Version.html`, read as stored at publication. Never produced again (FR-010, Article XIII) |
| `ip_address` | `str \| None` | `research.md` R8. Present only where the record holds one, so a site that never turned FS-003's setting on shows nothing and records written before it was turned on look exactly as they did |

**`Section`** — one kind of record the package holds about a person.

| Field | Type | Why |
|---|---|---|
| `heading` | `str` | What the page calls this kind of record, translated |
| `entries` | `tuple[AcceptanceEntry, ...]` | The records themselves, in the order they happened |
| `template` | `str` | The partial that renders these entries. It is what makes the page a loop over sections rather than a page about acceptances (FR-017) |

**`PersonalRecord`** — the answer.

| Field | Type | Why |
|---|---|---|
| `subject` | `str` | The identifier the answer was produced for, so a reader can see which person was asked about (`research.md` R3) |
| `sections` | `tuple[Section, ...]` | Every kind of record held. FR-017: a further kind joins here and nothing else moves |
| `is_empty` | property | `True` when no section holds an entry. FR-005: a normal answer, not an error |
| `coverage` | property | FR-015's statement, carried by the answer rather than only by the page, so any later route carries it too. Present when empty as well (US-5 scenario 2) |

`produce(subject: str) -> PersonalRecord` is the only way one is built:

```python
acceptances = (
    Acceptance.objects.for_subject(subject)
    .select_related("version", "version__document")
)
```

One query (`research.md` R5), ordered by `Acceptance.Meta.ordering`, which is `["accepted_at",
"id"]` and therefore total. Each row becomes an `AcceptanceEntry`; the rows become one `Section`;
the section becomes the answer. Nothing else is queried and no clock is read, which is what makes
FR-006 hold (`research.md` R4).

**FR-017 in practice.** When R8 brings cookie choices, `produce()` gains a second builder call and
a second partial. `PersonalRecord` does not change, `is_empty` does not change, the page does not
change, and a consumer walking `record.sections` does not change. There is no registry, no hook and
no entry point — FR-018 forbids one, and `decisions.md` D1 is explicit that the requirement is a
constraint on the design rather than a licence to build a plugin system for one caller.

### Naming a person

`resolve_subject(text: str) -> str` in the same module, with the resolution order from
`research.md` R3: the user model's `USERNAME_FIELD`, then `email` where the user model has one
(case-insensitively, and only when exactly one account matches), then the text itself.

Step three is what US-4 rests on. A removed account has no row to look up, so the only way to ask
about that person is the identifier their records still carry — and a question about somebody the
package has never heard of lands on a subject with no records, which is FR-005's answer rather than
an error.

### The route

One address: `/admin/mvp_compliance/disclosure/`.

`Disclosure` is a proxy of `Acceptance` (`Meta.proxy = True`) with no fields of its own. It exists
for three things a `ModelAdmin` needs and this package has nowhere else to put: an entry in the
admin index, an address, and a permission. `verbose_name_plural` is what the index shows, so it
reads as the question somebody fielding a request is asking rather than as a model name.

`Meta.permissions = [("produce_disclosure", _("Can produce everything held about a person"))]`. A
proxy gets its own content type, so this permission is the proxy's and holding `view_acceptance`
grants nothing on it (`research.md` R2, verified against Django 5.2.17's `create_permissions`).
Django also creates the routine `add`/`change`/`delete`/`view_disclosure` permissions for the
proxy. They are unavoidable and they grant nothing here.

`DisclosureAdmin`:

- `has_view_permission()` and `has_module_permission()` both return
  `request.user.has_perm("mvp_compliance.produce_disclosure")` — so the index entry appears only
  for somebody who may use it, and `view_disclosure` opens nothing.
- `has_add_permission()`, `has_change_permission()` and `has_delete_permission()` return `False`.
- `changelist_view()` is replaced outright and never calls `super()`. There is no `ChangeList`, no
  queryset over acceptances and no list of anybody's records — the page is the field and, when one
  was asked for, the answer. It raises `PermissionDenied` itself, because the admin's URL wrapper
  only checks that the caller is active staff.

**The request is a GET**, with the person in the query string, and it is the whole of the page's
behaviour. Producing an answer changes nothing, so a POST would be the wrong verb; a reload
re-produces the answer, which is FR-006 in the open. `decisions.md` records the one cost: the
identifier appears in the request line a server logs, as every admin object address already does.

**Every refusal is identical and precedes every lookup**, which is FR-013 and SC-004 for free:

| Caller | What happens |
|---|---|
| Not signed in | The admin's own redirect to its login page |
| Signed in, not staff | The same redirect |
| Staff, holding every other permission this package defines including `view_disclosure` | `PermissionDenied` |
| Staff holding `produce_disclosure` | The page |

Nothing about the named person is read before that check, so a refusal for somebody with records
and a refusal for somebody without them are the same bytes.

### The page

`admin/mvp_compliance/disclosure/produce.html`, built on `admin/base_site.html` like FS-002's
preview and publish pages:

- The field, and what may be typed into it, as `help_text`.
- When an answer was asked for: the subject it was produced for, the statement of coverage, and a
  loop over its sections, each including its own partial. When the answer is empty: the statement
  that nothing is held, and the same statement of coverage — US-5 scenario 2, because "nothing
  here" is not "nothing anywhere".
- `admin/mvp_compliance/disclosure/acceptances.html` renders one section's entries: the document,
  the version, the moment, the address where a record holds one, and the wording in full, marked
  safe (`research.md` R6).

No "produced at" stamp anywhere (`research.md` R4), and no download: a page carries the wording in
full and can be printed, a second route would need its own permission test under SC-003, and
`decisions.md` records the choice.

### What this feature does not add

- No model, no field, no stored row — `Key Entities` in the spec says so, and the migration creates
  only a proxy.
- No management command. It would be a route with no request and no user to check a permission
  against, which FR-012 and SC-003 cannot be satisfied for honestly.
- No `mvp_compliance/urls.py`. `tests/test_app.py` asserts on main that the package serves no
  address of its own, and that stays true.
- No changelist of acceptances, here or anywhere. That is R10's, and an ungated one is exactly the
  risk US-3 closes.

## Phases

**Foundational**: none. Everything this feature reads is on main from FS-001 and FS-003, and the
two fixtures the tests need belong to the story that introduces the permission.

Then the stories in priority order, one at a time in the main checkout. US-1 and US-2 are the
answer, US-3 is the route that produces it, US-4 and US-5 are properties of both.

| Story | Priority | What it adds |
|---|---|---|
| US-1 | P1 | `records.py`: `AcceptanceEntry`, `Section`, `PersonalRecord`, `produce()`; one query; the empty answer; the same answer twice; `docs/models.md` |
| US-2 | P1 | `wording` on each entry, read from the stored HTML; the superseded-wording and per-entry-wording guarantees; the assertion that nothing is re-rendered |
| US-3 | P1 | `Disclosure`, its migration and its permission; `DisclosureForm`; `DisclosureAdmin` and both templates; `resolve_subject()`; every refusal; `docs/disclosure.md` and the README |
| US-4 | P2 | The answer for a person whose account is gone, under both of FS-003's settings, and the documentation of what survives |
| US-5 | P1 | `coverage` on the answer and on the page in both states; the sweep that keeps a regulation's name out of the page and its documentation; the CHANGELOG entry |

US-4 is expected to need no production code — `produce()` filters on `subject`, which is the
identifier that survives — so its tasks say so, and the reviewer is asked to confirm the claim
holds in the code rather than accept that the tests pass. A story that adds only tests is the shape
most likely to hide a vacuous one.

**Convergence** (S5, Forge): squash this branch's migrations into one, run the cleanup pass over the
feature diff, and record an ADR verdict for every entry in `decisions.md`.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| A proxy model that carries no table | A `ModelAdmin` needs a registered model, and this page needs an admin index entry, an address and a permission of its own | Registering `Acceptance` itself: it hands everyone holding `view_acceptance` a changelist of every person's consent history, which is the risk US-3 exists to close and the shape of R10. Hanging the page off `VersionAdmin`: no index entry, so nobody fielding a request finds it |
| The answer holds sections rather than a list of acceptances | FR-017's literal requirement: a further kind of record joins without the answer's shape changing | A field per kind: adding cookie choices changes the answer's shape and every consumer that walked it, which is the retrofit FR-017 names |
| A section carries the template that renders it | It is what lets the page be a loop over sections instead of a page about acceptances | A branch per kind in the template: the page has to be edited for every kind that joins, which is the thing FR-017 asks to avoid |
| The person is named by free text rather than chosen from a list of accounts | US-4: a record can outlive the account it names, and there is then no account to choose | A user picker: it cannot express the one case this story exists for, and a second field for "or the identifier on the records" makes the ordinary case worse to serve the rare one |
| The answer carries no time of its own | FR-006 and SC-005: the same answer twice | A produced-at stamp: it is what people expect on a printed answer, and it makes FR-006 false by construction |
