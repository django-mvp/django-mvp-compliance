# Implementation Plan: A person downloads a copy of their data

**Branch**: `012-copy-of-own-data` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

## Summary

A setting, `MVP_COMPLIANCE_PERSONAL_DATA`, lists dotted paths to subclasses of
`mvp_compliance.personal_data.PersonalData`. Each one is a kind of record the project holds about
a person: a heading, a description, and a way to collect one person's rows, by default a model,
its fields and `get_queryset(user)`. `PersonalDataCopy` builds the download: a zip holding
`index.html` (the approved readable layout, stylesheet inlined), `data.json` and `files/`. The
account-area page `PersonalDataView` lists the kinds and offers the download. It is guarded by
django-allauth's `reauthentication_required`, so opening it asks a person who has not confirmed
recently to do so first. A failing kind gives no download and is logged. A signal,
`personal_data_copied`, tells the project after each download.

## Technical context

Python 3.12+, Django 5.2 to 6.1, as the CI matrix says. One new optional dependency:
`django-allauth>=65.19,<66` under the extra `personal-data`, justified in research.md
("Confirming identity"), and added to the `dev` dependency group for the tests and the demo. No
model in the package, no package migration. Tests with pytest and pytest-django, settings
`tests.settings`.

## Constitution check

- **Article I, testing**: every task that changes behaviour starts from a failing test. Wording,
  layout and the readable copy's markup are not tested (testing.md §1). What is tested is what the
  copy holds and does not hold.
- **Articles II and III, simplicity**: one base class, one builder, one view, one signal, one
  check. No registry: the setting is the list (research.md, N1).
- **Article VII, dependencies**: allauth is optional and imported only where the page needs it.
  deptry passes with it declared in the extra.
- **Article X, cohesion**: collecting rows is `PersonalData`'s, building the zip is
  `PersonalDataCopy`'s. No module-level helpers sharing a subject.
- **Article XII**: the wording in the copy is `Version.html`, read through `records.produce()`.
- **Article XIII**: the package gathers nothing from another app's models itself. Every project
  row comes through a class the project declares. No wording claims completeness or names a
  regulation.
- **Article XIV**: nothing is stored. The signal passes the user to the project's own code, which
  gets a CHANGELOG entry naming it.
- **Article XV**: a project that does not set the setting sees no page, no route and no menu
  entry.

## Design

### Declaring a kind

```python
# settings.py
MVP_COMPLIANCE_PERSONAL_DATA = [
    "accounts.personal_data.Profile",
    "datasets.personal_data.Datasets",
]

# datasets/personal_data.py
from mvp_compliance.personal_data import PersonalData

class Datasets(PersonalData):
    heading = _("Datasets you uploaded")
    description = _("Every dataset you uploaded, with its file.")
    model = Dataset
    fields = ["title", "licence", "created", "upload"]
    file_fields = ["upload"]

    def get_queryset(self, user):
        return Dataset.objects.filter(owner=user)
```

`mvp_compliance/personal_data.py`:

- `PersonalData`: class attributes `heading`, `description`, `model = None`, `fields = []`,
  `file_fields = []`, `single = False`, `template_name = None`. `key` defaults to the class name
  in lower case, used for the section's anchor and its folder under `files/`.
- `get_queryset(user)`: raises `NotImplementedError` unless overridden. No default filter is
  guessed, because which field points at the person is the project's knowledge.
- `collect(user)`: returns a `PersonalDataSection`. The default reads `get_queryset(user)` and,
  for each object, each declared field: its `verbose_name` as the label, `get_<name>_display()`
  for a field with choices, `str()` for a relation, the raw value otherwise, `None` for an empty
  value. A `file_fields` value with a file becomes a `CopiedFile(path, name, field_file)`.
  Overriding `collect` is the escape for data that is not one queryset.
- `PersonalDataSection`, a frozen dataclass: `key`, `heading`, `description`, `single`,
  `template_name`, `columns` (tuple of `(name, label)`), `rows` (tuple of tuples of values).
- `get_personal_data()`: reads the setting, `import_string`s each path, instantiates it, and
  returns the list. `None` when the setting is absent, `[]` when it is empty. The one module-level
  function, a thin wrapper as Article X allows.

The package's own section is built by `AgreementsPersonalData`, a subclass in the same module
whose `collect` reads `records.produce(str(user.pk))`. It is always last and never declared.

### Building the copy

`PersonalDataCopy(user, sections, made_at, site_name, theme)` in the same module:

- `write(file)`: writes the zip to a binary file object. `index.html` from
  `mvp_compliance/copy/index.html` with the stylesheet read through `staticfiles_storage`,
  `data.json` with `DjangoJSONEncoder`, then each `CopiedFile` copied in with `shutil.copyfileobj`.
- File paths are `files/<key>/<pk>/<file name>`, so no two collide.
- `data.json`: `{"made_at", "person", "sections": [{"key", "heading", "fields": {name: label},
  "records": [{name: value}]}]}`. A file value is its path inside the zip.
- `PersonalDataCopy.collect(user, kinds)`: collects every kind before anything is written. An
  exception from a kind's `collect()` is raised as `PersonalDataError` naming the kind's dotted
  path, from the original. So is one from a file's `open()` during `write`.

### The page

`PersonalDataView(LoginRequiredMixin, MVPTemplateView)` in `views.py`:

- `dispatch` is wrapped with allauth's `reauthentication_required` (no `allow_get`) through
  `method_decorator`, imported where the view is defined, guarded so the module still imports
  without allauth. 404 when the account area is not mounted, as `AgreedDocumentsView`.
- `get`: the headings and descriptions of the kinds and the button. Nothing collected.
- `post`: builds the copy into a `SpooledTemporaryFile`, returns a `FileResponse` attachment named
  `copy-of-your-data-<date>.zip`, then sends `personal_data_copied` with `send_robust` (sender
  `PersonalDataView`, `user`, `kinds` as the list of keys), logging a failed receiver. On
  `PersonalDataError`: `logger.exception` naming the kind, then the page again with the failure
  alert, status 500.
- The route `data/` (name `personal-data`) is in `urls.py` only while the setting is set. The menu
  entry is appended in `menus.py` and dropped by the menu when the route is absent (ADR 0020).

### The system check

`check_personal_data` in `checks.py`, registered in `ready()`, silent while the setting is absent:

- `mvp_compliance.E005`: the setting is not a list or tuple.
- `mvp_compliance.E006`: a path cannot be imported, or does not name a `PersonalData` subclass.
  One error per path, naming it.
- `mvp_compliance.E007`: a kind with `model` set names a field in `fields` or `file_fields` that
  the model does not have, or a `file_fields` entry that is not a `FileField`.
- `mvp_compliance.E008`: `allauth.account` is not installed, or its `AccountMiddleware` is not in
  `MIDDLEWARE`.

### Templates

Kept from the sketch as approved: `personal_data.html` with the password form removed and the
button in its place, `copy/index.html`, `cotton/compliance/copy_value.html`. A kind with
`template_name` is rendered by including its template with the section in context, in place of
the standard table or pairs. The sketch's stub module, its `?state=` switches, its
`ConfirmIdentityForm`, `demo/backends.py` and the `data/copy/` route are removed.

### The demo

- allauth installed with email or username sign-in.
- `demo.models.Upload` (title, licence with choices, uploaded, file, owner), with its migration,
  declared as a kind. A `Profile` kind reads the user's own row (name, email, date joined) with
  `single = True`.
- `seed_demo` gives `veteran.user` and `regular.user` uploads with small real files, one record
  with no file, two files of the same name. `MEDIA_ROOT` under the demo, git-ignored.

### Documentation

`docs/personal-data.md` (how-to: declaring kinds, overriding `collect`, a kind's own template,
the signal, the allauth requirement), `README.md` setting entry, `CONTEXT.md` terms *Copy* and
*Declared kind*, `CHANGELOG.md` *Added* naming the data the signal passes on. ADRs for the split
from ADR 0012 and for requiring allauth, graduated at converge.

## Order

US-2 first, because the page has nothing to list without a declaration. Then US-1, then US-3.
