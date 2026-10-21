# Sketch — FS-012

## What exists

- The account area is django-mvp's: `mvp/account/base.html` puts a page in the narrow container
  beside `AccountCenterMenu`. The package already has one page there, `AgreedDocumentsView`
  (`/legal/agreed/`), built from `c-mvp.page`, `c-mvp.page.title` and `c-mvp.card`, with one menu
  entry appended in `mvp_compliance/menus.py`.
- `mvp_compliance.records.produce(subject)` already assembles the person's acceptances with the
  wording stored at publication, as one `Section`. The copy's own section is built from it.
- The demo project has no allauth. Its sign-in is django-mvp's stand-in, so the sketch confirms a
  person's identity by asking for their password.
- The shell's stylesheet is `mvp/static/css/django-mvp.css`. The readable copy carries it inline so
  it opens with no network and looks like the site in the site's default theme.

## Design rationale

Written before the build. Class: **convention** (a source settles it) or **taste** (a choice).

1. The page lists what the copy holds, one row per kind, with a heading and one line saying what
   it is, and no counts. **Convention**: FR-003, opening the page gathers nothing, so a count is
   not available without breaking it.
2. The password is asked for on the page itself, in the same form as the button, rather than on a
   separate step. **Taste**: one step for a one-field confirmation. allauth's reauthentication,
   where a project has it, sends the person to its own page and back, which research settles.
3. Once a person has confirmed recently, the form shows only the button. **Convention**: US-1
   scenario 4.
4. The failure message sits above the page title. **Convention**: the project's own pattern
   (alerts go above the title, `agreement.html`).
5. The button says what it does and carries the download icon. **Convention**: GOV.UK button
   guidance, a button names its action.
6. The readable copy opens with when it was made and for whom, then a list of contents linking to
   each kind. **Convention**: a long standalone document needs a way in (GOV.UK contents list
   guidance).
7. A kind with one record, such as a profile, shows as label and value pairs. A kind with several
   shows as a table, one row per record. **Convention**: tables are for comparing records with the
   same attributes (NN/g, "tables"). One record has nothing to compare.
8. A missing value shows as an em dash. **Convention**: the project's rule for missing
   information.
9. The wording a person agreed to is folded under each acceptance. **Taste**: the wording is long
   and the dates are what a reader scans for first. Printing unfolds nothing, which research may
   want to revisit.
10. The copy uses the site's default theme and never the person's chosen one. **Taste**: the file
    outlives the setting.
11. The package's own section, the documents the person agreed to, comes after the project's
    kinds. **Taste**: a person opening a copy looks for their own content first.
12. The download is named `copy-of-your-data-<date>.zip`. **Taste**: the date tells two copies
    apart in a downloads folder.

## What the screens need from the code

- The page needs every declared kind's heading and one-line description, without gathering any
  records.
- The page needs to know whether the person confirmed their identity recently.
- The copy needs, for each kind, its records with each detail's label and the value as a person
  reads it on the site, and whether the kind is one record or several.
- The copy needs each uploaded file's path inside the download, unique across every kind.
- The copy needs the site's name, the time it was made, the person's sign-in name and the site's
  default theme.
- The copy needs the shell's stylesheet as text, to carry it inline.
- The machine-readable part needs each detail keyed by its field name, not its translated label.
  The sketch uses labels.

## What the sketch faked

- Every project kind (profile, datasets, comments, messages) is stub data in
  `demo/sketch_copy.py`. Nothing is declared, and there is no declaration setting or base class.
- The files in the download are a few bytes of placeholder text, not real uploads.
- `?state=confirmed`, `?state=failed` and `?state=nothing` on the page switch between states. In
  the build they come from the session, a real failure and real records.
- `/legal/data/copy/` serves the readable part in the browser so it can be looked at without
  unzipping. It is not part of the feature.
- The password check is Django's `check_password` with no record of when it succeeded, so
  `?state=confirmed` stands in for "recently confirmed".
- The project is told nothing when a copy is downloaded (US-3).

## What was ruled by eye

Nothing yet.
