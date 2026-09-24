# AGENTS.md — Agent Configuration for django-mvp-compliance

<!-- Thin index only — bloat here = ignored instructions. Details live in the pointed-to files. -->

django-mvp-compliance manages the legal documents a site publishes and records what people agreed
to. Documents are written in Markdown, held in the database, and published as pages rendered in the
django-mvp shell. `CONTEXT.md` defines the terms; use them, especially the distinction between a
document, a version of it, and an acceptance of that version.

**A published version is immutable.** Nothing in this package may offer a path that edits one, and
no convenience is worth an exception. A correction is a new version. An acceptance points at a
version, never at a document, and is never edited or deleted.

This package does not make anyone compliant, and no code, comment, docstring or user-facing string
may claim it does. It provides mechanics: publishing, recording, enforcing. Whether the documents
say the right things is the host project's problem.

Data subject access requests are a surface here, never an implementation. The package can show a
person what it holds and expose hooks. It never gathers or erases data belonging to other apps.

## Stack & commands

- **Stack:** Python 3.12+ / Django 5.2, 6.0 and 6.1, uv-managed (hatchling build backend), built on django-mvp and Cotton
- **Install:** `uv sync`
- **Test:** `uv run pytest`
- **Lint:** `uv run pre-commit run --all-files` (ruff lint + format, mypy, deptry)
- **Type-check:** `uv run mypy`
- **Build:** `uv build`
- **Demo project:** `uv run python manage.py runserver 0.0.0.0:8021`

Lint is the pre-commit run, not a bare `ruff check .`: the hook config excludes `docs/` and
migrations, and a raw invocation reports findings in paths the gate does not cover.

## Data model rules

Immutability is enforced in the model layer, not by convention and not only in the admin. A
published version rejects writes to its content, and an acceptance rejects writes outright. Any
feature that needs to change what a published version says is asking for a new version.

A version stores both the Markdown a person wrote and the HTML that was rendered from it at
publication. The rendered HTML is the evidence: it is what a reader was served, and re-rendering
from source years later can produce something different after a Markdown library upgrade. Serve
the stored HTML, never a fresh render.

Migrations are consolidated per pull request, and every field carries `verbose_name` and
`help_text`. See `CONSTITUTION.md`.

## Agent skills

### Issue tracker

Issues tracked in GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary mapped 1:1 to canonical roles (needs-triage, needs-info, ready-for-agent,
ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — one `CONTEXT.md` at root and `docs/adr/` for architectural decisions.
See `docs/agents/domain.md`.

### CI checks

CI runs from the shared reusable workflows in `django-mvp/shared`, pinned at `v0.4.1`. Because
they are called rather than inlined, those status checks carry their caller job as a prefix.
The required checks are:

- `call-build / Code Quality`
- `call-build / Security Scan`
- `call-build / Build Package`
- `call-tests / Test Python 3.12, Django 5.2`
- `call-tests / Test Python 3.12, Django 6.0`
- `call-tests / Test Python 3.13, Django 5.2`
- `call-tests / Test Python 3.13, Django 6.0`

`tests.yml` and `build.yml` deliberately carry no `paths:` filter on `pull_request`. A required
check that is filtered out never reports, and a check that never reports blocks the merge.

## Releasing

Releases run through the shared release flow, never by hand and never by pushing a tag.

1. Dispatch **Prepare Release** with a bump level. It opens a pull request carrying the version
   bump and the CHANGELOG section.
2. Merging that pull request is the release decision. **Tag Release** then cuts the tag and the
   GitHub Release from the merge commit.
3. **Publish** uploads to PyPI through trusted publishing. PyPI's trusted publisher is bound to
   the `publish.yml` filename — renaming that file breaks publishing until the PyPI project
   settings are changed to match.

`pyproject.toml` holds the version and is the single source of truth for all three steps.

Nothing has been released. Two things are needed before the first release: a PyPI trusted publisher
for this project pointed at `publish.yml`, and a `RELEASE_TOKEN` that can write to this repository.

**Tag Release skips a version with no matching CHANGELOG section**, which is what keeps the seed
version from being cut as a release. Leave the scaffold version under `## [Unreleased]` until
Prepare Release promotes it — writing a `## [0.0.1]` heading by hand makes the next push to
`pyproject.toml` tag and release it.

## Development workflow

Feature work follows a spec-driven process: spec → plan → tasks → implement → review → pull
request, with `specs/NNN-slug/` directories generated per feature. Project standards and the
quality bar live in `CONSTITUTION.md`.

`docs/brainstorm.md` holds the working notes the package was founded on: the prior-art survey,
what overlaps with existing packages, and why it was built anyway. Those are conclusions, not
ratified decisions. Anything that hardens goes to `CONSTITUTION.md` or an ADR.
