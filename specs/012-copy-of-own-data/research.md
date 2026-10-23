# Research — FS-012

Done against main at `5280944` (v0.3.0, django-mvp 0.30), after the sketch was approved.

## Planning notes, answered

### N1 — Flexible for host projects, consistent for people

**Adopted.** A project lists dotted paths in `MVP_COMPLIANCE_PERSONAL_DATA`. Each names a subclass
of `mvp_compliance.personal_data.PersonalData`, shaped like a Django generic view:

- `model`, `fields` and `get_queryset(user)` cover the common case. Labels come from each field's
  `verbose_name` and values from the field itself: `get_<field>_display()` for a field with
  choices, `str()` of a related object, the date and time formats Django already applies.
- A `FileField` named in `fields` puts its file into the download. Each file is read through
  the field's own storage, so files kept on S3 or another backend work the same as local files.
- `collect(user)` is the override for data that is not one queryset. It returns a
  `PersonalDataSection` and the package presents it like any other kind.
- `template_name` gives a kind its own presentation in the readable part only. The
  machine-readable part is always built the same way.
- `heading` and `description` are what the page and the copy show for the kind.

Following `AUTH_PASSWORD_VALIDATORS` and `django.contrib.auth.password_validation`, the list is
loaded with `import_string` and instantiated once per request. Considered and not adopted:
registering kinds from each app's `AppConfig.ready()`. A registry decides the order by import
order and lets an app add itself to every project that installs it, which is exactly what
Article XIII says the project decides. A setting puts the whole contents of the copy in one place
the project owns.

The readable part reuses the sketch's layout. One record shows as label and value pairs, several
as a table, a missing value as an em dash, and the package's own section last. All of it is the
templates Sam approved.

### N2 — The same declaration should serve deletion later

**Adopted as a constraint, nothing built.** `PersonalData` takes a user and never a request, and
carries no state between calls, so #48 can add `erase(user)` to the same class. Nothing in this
plan names the class after copying ("export", "download") for that reason.

### N3 — Built on the spot now, in the background later

**Adopted as a constraint.** The copy is built by `PersonalDataCopy`, a plain class taking a user
and the time it is made, which writes the zip to a file object. The view calls it and returns
the file. A background task in #116 calls the same class and keeps the file. Nothing in it
reads the request.

## What the sketch needs and faked, answered

| Item | Answer |
|---|---|
| Each kind's heading and description, without gathering records | `PersonalData.heading` and `.description` are class attributes. The page instantiates the classes and reads them, and never calls `get_queryset` or `collect`. |
| Whether the person confirmed their identity recently | Delegated to django-allauth (below). The page is not shown until they have. |
| Each kind's records, labelled, as a person reads them | `PersonalData.collect(user)` returns a `PersonalDataSection` of labelled columns and rows. The default implementation reads `fields` from `get_queryset(user)`. |
| One record or several | `PersonalData.single`, default `False`. A profile sets it. |
| Unique file paths in the download | `files/<kind key>/<record pk>/<file name>`. The primary key keeps two files with one name apart, inside a kind and across kinds. |
| Site name, time made, sign-in name, default theme | Site name from `MVP_CONFIG`'s sidebar title, which the shell already shows, else the request host. Time from `timezone.now()` once. Sign-in name from `get_username()`. Theme from `MVP_CONFIG["theme"]["default"]`. |
| The site's stylesheet as text | `django.contrib.staticfiles.finders.find("css/django-mvp.css")`, opened from the installed package. It works in tests, development and production with no `collectstatic`. `staticfiles_storage.open` was checked and rejected: it raises without `STATIC_ROOT`. |
| JSON keyed by field name | `data.json` keys each value by the field's name. The label goes alongside it once per kind, under `fields`. |
| Stub project kinds | The demo declares two real kinds against a model of its own (`demo.Upload`, with a file) and the user's own row. |
| Placeholder files | Real `FileField` uploads in the demo, seeded by `seed_demo`. |
| `?state=` switches | Removed. Confirmed comes from allauth, failure from a kind that raises, nothing held from a user with no records. |
| Readable copy served in the browser | Removed. The walkthrough opens `index.html` from the downloaded zip. |
| Password check without memory | Removed with the form. allauth's reauthentication remembers when. |
| Project not told | `mvp_compliance.signals.personal_data_copied`, sent with `send_robust` as `version_published` already is, so a failing receiver never stops the download. |

## Confirming identity

The sketch review asked for confirmation to be a step of its own, the way django-allauth guards
its sensitive pages.

allauth's public API for this is `allauth.account.decorators.reauthentication_required`
(django-allauth 65.19, `allauth/account/decorators.py:62`). Applied to a view, it raises
`ReauthenticationRequired` for a signed-in person who has not authenticated within
`ACCOUNT_REAUTHENTICATION_TIMEOUT` (300 seconds by default). allauth's `AccountMiddleware` turns
that into a redirect to its own confirmation page, which sends them back afterwards. Without
`allow_get`, opening the page is what asks. That is the behaviour of allauth's email and
password pages, and it is what was asked for.

**Decision: the page requires django-allauth.** Considered and not adopted: a confirmation page
of the package's own for sites without allauth. It would be a second password form with no rate
limiting, no support for a second factor or for accounts that sign in through another provider,
and no shared memory with allauth's own record of when a person last confirmed. Projects on
django-mvp sign in through django-mvp-accounts, which installs allauth, and django-mvp's own
sign-in is a development stand-in. allauth becomes an optional extra,
`django-mvp-compliance[personal-data]`, imported only by the module the page lives in. A system
check reports an error when the setting is declared and `allauth.account` is not installed, or
its middleware is missing.

What allauth does for an account with no password (one that signs in only through another
provider) is to treat it as recently confirmed (`did_recently_authenticate`, the comment at
`allauth/account/internal/flows/reauthentication.py:76`). That is allauth's documented position
and the package follows it rather than adding a stricter rule of its own. It settles the spec's
open assumption.

## Building the copy

- **Zip:** `zipfile.ZipFile` over a `tempfile.SpooledTemporaryFile` (10 MB in memory, then disk),
  returned as `FileResponse(as_attachment=True, filename=…)`. Uploaded files are copied in with
  `ZipFile.open(name, "w")` and `shutil.copyfileobj` from `field.open("rb")`, so no file is held
  in memory whole. The temporary file is deleted when the response closes it (FR-008).
- **Readable part:** `render_to_string` of the approved template with the stylesheet inlined.
- **Machine-readable part:** `json.dumps(…, cls=DjangoJSONEncoder)`, which already handles dates,
  decimals and UUIDs.
- **Failure:** every kind is collected before anything is written. Any exception from a kind or
  from opening a file is logged with `logger.exception` naming the kind's dotted path, and the
  view re-renders the page with the error alert, status 500, nothing downloaded (FR-018, FR-019).
  The person's message is the approved fixed sentence.
- **The package's own section** reads `records.produce()`, so the acceptances and their stored
  wording are exactly what the staff page shows (FR-021, Article XII).

## Whether the page exists

`mvp_compliance/urls.py` adds the `data/` route only when `MVP_COMPLIANCE_PERSONAL_DATA` is set,
the same way django-mvp adds its installable-app routes only while `MVP_CONFIG["pwa"]` is set.
The menu entry needs nothing: an entry whose address does not resolve is dropped (ADR 0020).
The page also answers "not found" when the account area is not mounted, as the agreements page
does.

## What already exists

| Piece | Stopped at | Found |
|---|---|---|
| Asking for identity again | 3, an installable package | `allauth.account.decorators.reauthentication_required` |
| Loading a list of classes from a setting | 4, Django | `django.utils.module_loading.import_string`, as `password_validation.get_password_validators` |
| Field labels and choice display | 4, Django | `Field.verbose_name`, `Model.get_FOO_display()` via `field.flatchoices` / `display_for_field` from `django.contrib.admin.utils` |
| Formatting dates and numbers for a person | 4, Django | `django.utils.formats.localize` |
| JSON for dates and decimals | 4, Django | `django.core.serializers.json.DjangoJSONEncoder` |
| Zip and temporary file | 4, standard library | `zipfile`, `tempfile.SpooledTemporaryFile` |
| Streaming the download | 4, Django | `django.http.FileResponse` |
| The stylesheet as text | 4, Django | `django.contrib.staticfiles.finders.find` |
| The acceptances with their wording | 2, this repo | `mvp_compliance.records.produce` |
| Telling the project | 2, this repo | the `version_published` pattern in `signals.py`, `send_robust` |
| Account-area page, breadcrumbs, 404 without the area | 2, this repo | `AgreedDocumentsView` |
| Menu entry | 2, this repo | `menus.py`, `AccountCenterMenu.append` |
| Folding the wording | 5, the browser | `<details>` |
| A value or an em dash in the copy | 7, new code | the `compliance.copy_value` component from the sketch |
| `PersonalData` base class | 7, new code | nothing does it. The few lines that turn a queryset into labelled rows are the class. |
| `PersonalDataCopy` builder | 7, new code | the zip layout is this feature's |

`display_for_field` is admin-internal (`django.contrib.admin.utils`) and is not adopted: the
package does not depend on the admin for a public page. `localize` plus `get_FOO_display` covers it.
