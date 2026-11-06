# Plan — 015 Translations of a published version

Spec: [spec.md](./spec.md) · Research: [research.md](./research.md) · Tasks: [tasks.md](./tasks.md)

## Summary

One new model, `Translation`, one row per wording of a version in one language, reusing the
guard, rendering, publisher and admin patterns `Version` already has. The frozen-field guard is
extracted from `Version` into a shared base so both models use the same code. No reader-facing
page changes.

## Technical context

Python 3.12+, Django 5.2 / 6.0 / 6.1, uv. No new dependency (research N1). One migration,
`0004_translation`, which only creates a table and adds no column to an existing one.

## Constitution check

| Article | How it holds |
|---|---|
| I (test first) | Every behaviour task in `tasks.md` is preceded by its failing test |
| VIII (i18n) | Every new string marked. `makemessages` over the package stays clean |
| XI (immutability) | A translation's frozen fields are guarded on the instance and the queryset, by the same code as a version's. Writing a translation never writes to `Version` |
| XII (stored HTML) | HTML is rendered once, when a translation is put live, and stored |
| XIII (no claim) | No string says a translation governs or is equivalent. The version page says the version's own text governs |
| XIV (personal data) | `publisher` + `publisher_subject` on `Translation`, with `help_text`, and a CHANGELOG entry naming them |
| XV (stored data) | The migration creates a table and touches no version or acceptance |

## Design

### Shared guard — `mvp_compliance/models.py`

Extract from `Version` into an abstract base `FrozenOnPublication(models.Model)` and a
queryset base `FrozenOnPublicationQuerySet`:

- `frozen_fields()`, `frozen_field_keys()`, `stored_row()`, `refuse_if_published_wording_changed()`,
  `save()` and `delete()` guards, parameterised by a class attribute `FROZEN_FIELDS` and the
  error message.
- Queryset `update()` and `delete()` guards and `published()` / `drafts()` / `current()`.

`Version` keeps its behaviour exactly: `PUBLISHED_FROZEN_FIELDS` becomes its `FROZEN_FIELDS`,
its manager still forwards explicitly (ADR 0006) and still has `use_in_migrations` (ADR 0004).
Behaviour-preserving: the existing suite is the proof, and no test is added for it.

### `Translation`

Fields: `version` (FK `Version`, `CASCADE`, `related_name="translations"`), `language`
(`CharField(max_length=15)`, no `choices`), `markdown`, `summary` (blank), `html`, `status`
(draft · current · superseded, the same values as `Version.Status`), `published_at`,
`publisher` (FK user, `SET_NULL`), `publisher_subject`. `verbose_name` and `help_text` on every
field. Frozen once published: `version`, `language`, `markdown`, `summary`, `html`,
`published_at`, `publisher`, `publisher_subject`.

Constraints: one current row per `(version, language)` (partial unique); a check constraint
tying status to `published_at` / `html`, as `Version` has. Meta permission
`("publish_translation", "Can put a translation live")`.

Manager `TranslationManager` (explicit forwarding, `use_in_migrations`), queryset adds:

- `live()` = current and `version__status != draft`.
- `with_replaced_at()` = `published_at` of the next published row for the same version and
  language.
- `missing_for(language)` is on `VersionQuerySet` instead (below).

Methods:

- `clean()` and `publish(publisher=None)` refuse, with `TranslationError` from `clean`'s rules
  and `PublishError` from `publish`'s: a language not offered (`offered_languages()`), the main
  language, a translated summary when the version has none, output that renders empty, a
  wording identical to the current one for the same version and language, a row that is no
  longer a draft (rechecked under `select_for_update()` on the version row).
- `publish()` supersedes the current row for the same version and language, renders and stores
  `html`, sets `published_at`, `publisher`, `publisher_subject`, inside one transaction.
- `live_since` property: the later of `published_at` and `version.published_at`, `None` while
  the version is a draft.
- `publisher_display` as on `Version`.
- `language_name` from `get_language_info`, and `is_offered` for the admin's flag (FR-015).

`offered_languages()` (module function, read at use): `[]` unless
`settings.is_overridden("LANGUAGES")`; otherwise `settings.LANGUAGES` without the code
`get_supported_language_variant(settings.LANGUAGE_CODE)` resolves to.

`VersionQuerySet.missing_translation(language=None)`: published versions with no live row in
that language, or in any offered language when `None`. One query.

### Exceptions

`TranslationError(Exception)` in `exceptions.py`, for a refused create or clean called from
code. `save()` calls the language check so `objects.create()` refuses too (US-2).

### Admin — `mvp_compliance/admin.py`

- `TranslationForm`: `markdown` (editor widget), `summary`, plus `version` and `language` as
  hidden fields on add, with `language` a `ChoiceField` built from `offered_languages()` at
  request time. `summary` hidden when the version has none.
- `TranslationAdmin`, on the `VersionAdmin` pattern: added only from a version
  (`?version=&language=`); a new correction starts from the current wording of that version
  and language; published rows read-only; preview and publish-confirmation views, the publish
  view checking `publish_translation` only; list shows version, language, status, live since,
  put live by; filters by language and status. Templates: `translation/change_form.html` and
  the preview and confirmation templates, reusing the version ones' blocks.
- `VersionAdmin`: a read-only `translations` field on the version's page listing each offered
  language with the live translation (link), a link to add one, or to correct it, plus any
  kept translation in a language no longer offered, flagged (FR-015). A list filter "Missing a
  translation" with one choice per offered language and one for any. Neither shown when
  `offered_languages()` is empty. Query count of the versions list unchanged by the number of
  translations (prefetch).

### Docs

`docs/authoring.md` gains "Translating a version" (what governs, the permission, correcting,
from code). `docs/models.md` documents `Translation`. `CONTEXT.md` gains *Translation*. FS-003
spec's "readings" becomes "translations". README feature list, `CHANGELOG.md` *Added* with the
Article XIV line.

## Project structure

```
mvp_compliance/models.py           shared guard, Translation, offered_languages, missing_translation
mvp_compliance/exceptions.py       TranslationError
mvp_compliance/forms.py            TranslationForm
mvp_compliance/admin.py            TranslationAdmin, VersionAdmin additions
mvp_compliance/migrations/0004_translation.py
mvp_compliance/templates/admin/mvp_compliance/translation/*.html
tests/test_models.py, tests/test_admin.py, tests/factories.py, tests/settings.py (LANGUAGES)
docs/authoring.md, docs/models.md, CONTEXT.md, README.md, CHANGELOG.md, specs/003-*/spec.md
```

## Complexity tracking

The shared guard is the one structural change outside the new code, and it removes the copy
that a second guarded model would otherwise need.
