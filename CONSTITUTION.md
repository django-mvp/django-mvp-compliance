# django-mvp-compliance Constitution

## Core articles

### Article I — Test-First
Every behavior change follows the traffic-light cycle: **Red** — write a test and watch it fail;
**Green** — write the least code that makes it pass; **Refactor** — clean up with the tests staying
green. No implementation before a failing test exists for the behavior. Tests accompany the change that
needs them; a pre-existing test is never modified or deleted to make new code pass, because it is
evidence about intent.

### Article II — Simplicity
Start with the simplest design that satisfies the spec. New dependencies, new abstractions,
and new infrastructure each require a stated justification in plan.md Complexity Tracking.
YAGNI over speculation.

### Article III — Anti-Abstraction
No wrapper layers, base classes, or "future-proofing" indirection without a present, concrete
second use. Prefer duplication over the wrong abstraction.

### Article IV — Integration-First
Contracts and integration points are designed and tested before internals are polished.
Acceptance scenarios exercise the system the way users touch it.

### Article V — Security & data-safety
Values interpolated into rendered output are escaped through the framework's template layer,
never hand-built string interpolation of model or user data. Secrets live in runtime config,
never in code, fixtures, or version control. Authentication, authorisation, cryptography and
permission changes never take a shortened review path.

### Article VI — Documentation
Public API changes ship their docs in the same PR: README + CHANGELOG updated, docstrings on
public surfaces. If the repo ships built docs, they must build clean.

### Article VII — Dependency discipline
A new runtime dependency requires a stated justification (Simplicity applied to the dependency
tree; prefer the shared toolchain bundle over ad-hoc dev dependencies). `deptry` must pass:
no unused, missing, or transitively-relied-upon dependencies.

### Article VIII — Internationalization
User-facing strings are translatable. In Python (models, forms, views, admin, template tags,
validators) they are wrapped with `gettext_lazy` (imported as `_`); templates load
`{% load i18n %}` and wrap strings with `{% trans %}` / `{% blocktrans %}`. Model `verbose_name`
/ `verbose_name_plural` and form `label` / `help_text` / `error_messages` use `gettext_lazy`; pure
acronyms are exempt. A package ships a base English (`en`) catalog and a `locale/` directory so
host projects can compile or extend translations. CI runs `makemessages` clean over the source as
the i18n gate; correct wrapper usage is otherwise enforced by review, and a hard-coded user-visible
string in a PR is a blocking comment. A package with no user-facing strings satisfies this
trivially.

### Article IX — Data-model conventions (Django)
Every model field is a deliberate indexing decision. Because consumers of a published package cannot
add their own indexes, any field with a plausible lookup / filter / ordering path is indexed at its
definition (`db_index`, `unique`, an FK's automatic index, or a composite `Meta.constraints` /
`Meta.indexes`); a field with no query path stays unindexed to avoid write cost. The choice —
indexed or not, and why — is recorded (plan `data-model.md` or `decisions.md`). `verbose_name` and
`help_text` are mandatory on every model field (Article VIII). **Migrations are consolidated per
PR:** the migrations a feature branch introduces are squashed into as few files as possible before
the PR is submitted (branch-local and unapplied, so safe at any release stage); data migrations
(`RunPython`/`RunSQL`) are exempt from auto-regeneration — keep them via `squashmigrations` or
standalone.

### Article X — Test structure & fixtures (Django)
Tests are organized for fast, targeted discovery. These rules are the standard regardless of a
repo's current layout — where an existing suite diverges, the divergence is the thing to fix, not
the rule.

- **Mirror the source tree.** Every test module mirrors the path of the module it exercises:
  `pkg/models.py` → `tests/test_models.py`; `pkg/views/form_views.py` →
  `tests/test_views/test_form_views.py`. Test subpackages carry `__init__.py` to match. When one
  source module defines several units (e.g. multiple models in a single `models.py`), it stays
  **one** `tests/test_models.py` — the per-unit split is expressed with classes (below), not with
  extra files (`test_concept.py` + `test_scheme.py` alongside a single `models.py` is
  non-compliant).

  **Exceptions — a test whose subject is not a Python module has nothing to mirror:**
  - *Test-only artifacts inside the tests package.* `tests/factories.py` is tested by a sibling
    `tests/test_factories.py` at the tests root, not mirrored to a package path.
  - *Package-level checks.* `tests/test_smoke.py` asserts that the package imports and its
    settings are valid. Its subject is the package as a whole.
  - *Non-Python subjects, declared by the repo.* A suite testing templates, static assets or
    another non-module artifact is exempt when the repo declares it:

    ```toml
    [tool.forge.conformance]
    non-mirror-paths = ["tests/test_components/"]
    ```

    A trailing slash marks a directory prefix. This is a **declaration, not a waiver**: it states
    that no source module exists to mirror, which is why it lives in the repo rather than in a
    conformance baseline (a baseline means "drift not fixed yet"). Declaring a path whose subject
    *is* a Python module is a review failure. The rule is deliberately not inferred — silencing
    every test directory that lacks a matching source package would also silence a misspelt one.
- **Group related tests into classes.** Within a module, tests are grouped into `Test<Subject>`
  classes — `class TestConceptModel:`, `class TestConceptSchemeModel:`, `class TestConceptManager:`
  — so one area can be targeted when debugging (`pytest tests/test_models.py::TestConceptModel`).
- **One factory per model.** Each model has exactly one `factory_boy` `DjangoModelFactory` in
  `tests/factories.py`, using `factory.Sequence` for uniqueness-guarded fields and
  `factory.SubFactory` for relations. Variants are **never** new factory subclasses
  (`ConceptWithoutSchemeFactory` is prohibited); they are expressed by overriding fields at the
  call site.
- **Fixtures wrap the factory; shared setup lives in conftest.** Reusable object fixtures are thin
  wrappers over the model's factory in `conftest.py` — `def concept(): return ConceptFactory()`,
  `def concept_without_scheme(): return ConceptFactory(scheme=None)`. A one-off variation needs no
  fixture: call the factory inline in the test (e.g. assert `ConceptFactory(scheme=None)` raises
  `ValidationError`). General setup and reusable fixtures live in `conftest.py`; test modules hold
  assertions, not construction boilerplate.
- **Use the pytest-django toolchain.** DB access via the `db` / `transactional_db` fixtures or
  `@pytest.mark.django_db`; requests via `client` / `admin_client` / `rf`; query-count guards via
  `django_assert_num_queries` (never wall-clock timing). `factory_boy` and `pytest-django` ship
  pinned in the `mvp-shared[test]` bundle — no per-repo pinning.
- **A run writes files only inside its own directory, and a factory attaches none unless asked.**
  Saving a model with a file writes it under `MEDIA_ROOT`, so `MEDIA_ROOT` — and `STATIC_ROOT`
  where anything writes to it — point at a directory the test runner creates for the run and
  removes afterwards (`tmp_path` / `tmp_path_factory`), never at a fixed path in the system
  temporary directory or in the working tree. Whatever is chosen has to hold under `pytest-xdist`,
  where each worker is a separate process. Separately, a factory that *can* attach a file leaves
  the field empty by default and writes nothing; a test that needs a real file asks for one
  (`ProjectFactory(with_image=True)`). The two are independent obligations. The first protects the
  repo holding the tests; the second is the only one that reaches a consumer, because a downstream
  project inherits a package's factories without inheriting its test settings, and a factory that
  writes on every build fills that project's media directory instead. Left unchecked this is not a
  tidiness problem: one suite put over 450,000 files in the system temporary directory and
  exhausted the machine's inodes, which presents as unrelated tooling failing while disk usage
  still looks healthy.

### Article XI — Cohesion (Python)
Related behaviour is grouped in a class, not scattered across module-level functions.

**The test:** two or more module-level functions that share a *subject* belong on a class. They
share a subject when they operate on the same data, take the same first argument, are only
meaningful in sequence, or are named around the same noun (`build_x`, `validate_x`, `render_x`).

**Why this is a standard and not a taste.** In a published package, a class is the extension
point. A consumer who needs different behaviour subclasses it and overrides one method. A module
of functions can only be monkey-patched, which is not a supported interface and breaks on any
internal change. Grouping also gives the behaviour a name, a place for shared configuration, and
one import instead of six.

**Shape:** shared state or configuration → a regular class holding it. Grouping for namespacing
with no shared state → still a class, with `@classmethod`/`@staticmethod`, or a small frozen
dataclass carrying the config. Expose a module-level convenience function only as a thin wrapper
over the class, never as the implementation.

**Django first.** Where the framework already owns the grouping, use it rather than inventing a
class: a `QuerySet`/`Manager` method instead of a function taking a queryset, a model method or
property instead of a function taking an instance, a `Form`/`Serializer` method instead of a free
validation function, a `TemplateView` method instead of a helper called by a view.

**Exceptions — narrow, and stated rather than assumed.** A genuinely standalone pure function with
no siblings. Framework-dictated module shapes: `conftest.py` fixtures, migrations, `urls.py`,
`apps.py`, decorator-registered template tags and filters, signal receivers, management-command
entry points. Factory functions that return the class. A module of independent utilities that
genuinely share no subject.

**This does not license abstraction.** Article III still holds: one class grouping today's
behaviour is the goal, not a base class, a registry, or a hierarchy built for a second
implementation that does not exist. Grouping related functions is organisation; adding a layer
between the caller and the work is not.

## Project articles


### Article XII — Published versions and acceptances are never written to

No code path changes the content of a published version, and no code path edits or deletes an
acceptance. The admin, management commands, data migrations and queryset methods are all covered.
A correction to a published version is a new version.

The refusal lives in the model layer: `save()`, `delete()`, and the queryset's `update()` and
`delete()`.

The one route that removes an acceptance is removing the account it names, when the host project
has configured acceptances not to survive that (ADR 0008).

### Article XIII — Pages serve the stored HTML

A version's HTML is rendered once, at publication, and stored. Every page and every answer serves
that stored HTML. Rendering Markdown at request time is prohibited.

Rendering goes through a sanitiser with an explicit allow list.

### Article XIV — No claim of compliance

No code, comment, docstring, user-facing string, template or document in this repository states or
implies that installing the package makes a site compliant with any regulation. Features, modules,
settings and templates are named for the mechanism (*recorded*, *published*, *enforced*,
*withdrawn*), never for a regulation.

Code in this package never gathers, exports or deletes data held in another application's
models. Anything the project holds is reached through a documented hook the project implements.

### Article XV — Personal data is declared

Every field that identifies or could re-identify a person states in its `help_text` what it is
for. Storing one that is optional is off by default and switched on by a setting.

A change that adds such a field, widens how long one is kept, or passes one to anything outside
the package ships with a CHANGELOG entry naming the data in plain language.

The package makes no outbound network request. Adding one is a change to this constitution.

### Article XVI — Compatibility

The package is pre-1.0 and the README says so. Model fields, template names and the public Python
surface may change between minor versions, and every such change is recorded in the CHANGELOG.
There are no compatibility aliases: an API is changed cleanly, and the CHANGELOG is how a consumer
finds out.

Stored data is the exception, and it does not get the same licence. A migration never drops or
rewrites a published version or an acceptance to accommodate a schema change. Where a model has to
change shape, the migration carries the existing records forward intact, and a migration that
cannot is a blocker rather than an acceptable loss.

Supported versions are Python 3.12 or later and the currently-supported Django releases, with the
CI matrix as the authoritative statement of both. Dropping either is a minor-version change with a
CHANGELOG entry. The django-mvp floor moves forward when a page needs something an older release
does not ship, and moving it is a CHANGELOG entry rather than a silent bump.

## Quality bar

Read at planning and at review; applies to every change.

- Test coverage: **project ≥ 90%, patch ≥ 85%**, per `codecov.yml`. These are floors, not a ratchet
  toward 100%.
- Every public API change updates README and CHANGELOG in the same pull request.
- `ruff check`, `ruff format --check`, `mypy` and `deptry` pass — through
  `pre-commit run --all-files`, which is the gate, rather than a bare invocation that reports
  findings in paths the hooks exclude.
- The package builds, its metadata is valid, and the README renders on the package index with
  absolute URLs.
- Immutability has a test that reinstates the defect: a change touching a published version or an
  acceptance is proven to raise, rather than proven to be absent from the code.

`djlint` is configured in `pyproject.toml` and can be run over `mvp_compliance/templates`, but it
is deliberately **not** a gate: it misfires against Cotton's `<c-vars>` syntax and needs ignore
rules first. Do not cite it as an enforced standard until it runs in CI.

## Non-negotiables

- Tests, build and lint pass before a change merges. Nobody overrides a red check.
- The default branch requires one approval, and the author of a change never approves it.

---

**Version**: 2.0.0 | **Ratified**: 2026-09-21 | **Last Amended**: 2026-09-24
