# Tasks — 012 A person downloads a copy of their data

Derived from [plan.md](./plan.md). Task ids are stable. Every task that changes behaviour follows
Article I: the failing test comes first. Tests find elements by fixture data, id or `data-` hook,
never by wording, and assert an error by its code or type, never by its sentence. The readable
copy's markup and wording are not tested. What it holds is.

Documentation is written in the story that introduces the public name.

Tests that need declarations use one `tests/conftest.py` fixture that sets
`MVP_COMPLIANCE_PERSONAL_DATA`, reloads `mvp_compliance.urls` and the test URLconfs that include
it, calls `clear_url_caches()`, and reloads again on teardown, as django-mvp-accounts'
`tests/conftest.py` does. It is written in T007. Kinds are defined under `tests/`.
`tests/settings.py` declares nothing. View-level assertions go in `tests/test_views.py`, the
builder's in `tests/test_personal_data.py`. The three stories edit the same modules and are built
one after another, never in parallel.

Order: US-2, then US-1, then US-3.

## Foundational

| Id | Task | Done when |
|---|---|---|
| T001 | Remove the sketch's scaffolding: `demo/sketch_copy.py`, `demo/backends.py` and its setting, `ConfirmIdentityForm`, `PersonalDataCopyView`, the `data/copy/` route, the `?state=` handling and the module-level helpers in `views.py`. Add `django-allauth>=65.19,<66` as the extra `personal-data` and to the `dev` group; `uv lock`. Install `allauth`, `allauth.account` and `AccountMiddleware` in `tests/settings.py` and `demo/settings.py`, with email or username sign-in in the demo; mount `allauth.urls` in `tests/urls.py`, each
`tests/urls_*.py` that serves a signed-in page, and the demo URLconf; fix any existing test that relied on django-mvp's stand-in sign-in | Full suite green; pre-commit green; `seed_demo` runs |

## US-2 — A developer declares what the project holds about a person (P1, issue #119)

| Id | Task | Done when |
|---|---|---|
| T002 | `tests/test_personal_data.py::TestCollect` — a kind declaring a test model, three fields and `get_queryset(user)` collects that user's rows only, in queryset order, with each column's label the field's `verbose_name` under `translation.override("de")` where the test model has a German catalogue entry, or the lazy label object otherwise (scenario 1, 2, FR-013, FR-014); a choice field yields its display value, a relation its `str()`, an empty value `None` (edge cases); a `FileField` named in `fields` with a file yields a `CopiedFile` whose path is `files/<key>/<pk>/<base name>`, two records with same-named files yield distinct paths, and an empty file field yields `None` (scenario 3, FR-015); `get_queryset` not overridden raises `NotImplementedError`; a kind overriding `collect` returns its own section (scenario 4, FR-023) | Fails before T003 |
| T003 | `mvp_compliance/personal_data.py`: `PersonalData`, `PersonalDataSection`, `CopiedFile`, `get_personal_data()`; test models in a `tests` app added to `INSTALLED_APPS`, with their migration, one factory per
model in `tests/factories.py` and a fixture for each in `tests/conftest.py` | T002 passes |
| T004 | `tests/test_checks.py::TestPersonalDataCheck` — no setting: no messages; a string: E005; an unimportable path and a class that is not a `PersonalData`: one E006 each naming the path; a field the model lacks: E007 naming the kind; two kinds with the same key: E006 naming both paths; allauth not installed (patch `apps.is_installed`) or its middleware absent: E008; a valid declaration: no messages (scenario 7, FR-017) | Fails before T005 |
| T005 | `check_personal_data` in `checks.py`, registered in `ready()`; messages translatable | T004 passes |
| T006 | Documentation for US-2: `docs/personal-data.md` (declaring, `collect`, `single`, `template_name`, the allauth extra), `README.md`, `CONTEXT.md` *Declared kind*, `CHANGELOG.md` *Added* | Docs check green |

## US-1 — Downloading a copy of my data (P1, issue #118)

| Id | Task | Done when |
|---|---|---|
| T007 | `tests/test_views.py::TestPersonalDataPage` — with the setting absent the route does not reverse and the account-area menu has no entry; with it set, the entry resolves (scenario 1, FR-001, FR-016); anonymous GET and POST redirect to sign-in and produce nothing (scenario 3, FR-009); a signed-in user who has not reauthenticated is redirected to `account_reauthenticate` on GET and POST, and no kind's `collect` is called (scenario 4, FR-010); after reauthentication GET lists every declared kind's `key` in order, then the agreements section, by `data-` hook, and calls no `collect` (scenario 2, FR-002, FR-003); the page answers 404 with no account area mounted, and 404 with `allauth.account` reported as not installed, calling no `collect`; the route accepts no argument (FR-011); an empty declaration shows the page with only the agreements section (US-2 scenario 6) | Fails before T008 |
| T008 | `PersonalDataView`, the conditional route, the menu entry, `personal_data.html` without the form | T007 passes |
| T009 | `tests/test_views.py::TestPersonalDataDownload` and `tests/test_personal_data.py::TestPersonalDataCopy` — POST after reauthentication returns a zip attachment holding `index.html`, `data.json` and each declared file at its path with the file's bytes (scenario 5, FR-004, FR-015); `data.json` holds every kind in declared order then the agreements, each record keyed by field name, the same records as `index.html` holds by `data-` hook (scenario 6, FR-005, FR-020); `made_at` is present; the agreements section holds each acceptance's document, version, time and `Version.html` exactly, including a superseded version (scenario 7, FR-021); a kind with no rows is present with no records, as is the agreements section for a user with none (scenario 8, FR-006); two users' copies hold nothing of each other's (scenario 9); after `response.close()` the streamed file is closed, `default_storage` holds the same files as before the request, and no row was written (scenario 11, FR-008, SC-006); a kind with its own `template_name` is rendered with it in `index.html` and has the standard shape in `data.json` (US-2 scenario 5, FR-024) | Fails before T010 |
| T010 | `AgreementsPersonalData`, `PersonalDataCopy`, `PersonalDataView.post`, `copy/index.html` and `copy_value` from the sketch, wired to sections | T009 passes |
| T011 | `tests/test_views.py::TestPersonalDataCopyFails` — a kind whose `collect` raises, a declared file that cannot be opened and a kind whose own template raises while rendering each give status 500, no attachment, the page with the failure alert by `data-` hook, and a log record at ERROR naming the kind's path with the original exception attached (scenario 10, FR-018, FR-019) | Fails before T012 |
| T012 | `PersonalDataError` and its handling in the view; the failure alert | T011 passes |
| T013 | The demo: `demo.models.Upload` and migration, `Profile` and `Uploads` kinds declared, `MEDIA_ROOT`, `seed_demo` uploads per plan.md. Documentation for US-1: `docs/personal-data.md` what a person sees and what the download holds, `CONTEXT.md` *Copy*, `CHANGELOG.md` | `migrate` then `seed_demo` on an empty demo database; the page and download work on the dev server |

## US-3 — A project hears about every copy made (P3, issue #120)

| Id | Task | Done when |
|---|---|---|
| T014 | `tests/test_views.py::TestPersonalDataCopiedSignal` — a receiver is called once per download with the user and the kinds' keys, the agreements section's included (scenario 1, FR-025); not called when the copy fails (scenario 2); a receiver that raises leaves the download intact and is logged (scenario 3, FR-026) | Fails before T015 |
| T015 | `personal_data_copied` in `signals.py`, sent from the view with `send_robust`; documented in `docs/personal-data.md`; `CHANGELOG.md` names the user passed to the project's code (Article XIV) | T014 passes; full suite green |
