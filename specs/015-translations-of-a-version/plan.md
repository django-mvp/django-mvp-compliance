# Plan — 015 Translations of a published version

Spec: [spec.md](./spec.md) · Research: [research.md](./research.md) · Tasks: [tasks.md](./tasks.md)

## Summary

One new model, `Translation`, one row per wording of a version in one language, reusing the
guard, rendering, publisher and admin patterns `Version` already has. `Version` is not changed. No reader-facing page changes.

## Technical context

Python 3.12+, Django 5.2 / 6.0 / 6.1, uv. No new dependency (research N1). One migration,
`0004_translation`, which only creates a table and adds no column to an existing one.

## Constitution check

| Article | How it holds |
|---|---|
| I (test first) | Every behaviour task in `tasks.md` is preceded by its failing test |
| VIII (i18n) | Every new string marked. `makemessages` over the package stays clean |
| XI (immutability) | A translation's frozen fields are guarded on the instance and the queryset, by its own guard naming `Translation`, as `VersionQuerySet` names `Version` (ADR 0004: the guard must hold on historical models in migrations, which carry no abstract base). Writing a translation never writes to `Version` |
| XII (stored HTML) | HTML is rendered once, when a translation is put live, and stored |
| XIII (no claim) | No string says a translation governs or is equivalent. The version page says the version's own text governs |
| XIV (personal data) | `publisher` + `publisher_subject` on `Translation`, with `help_text`, and a CHANGELOG entry naming them |
| XV (stored data) | The migration creates a table and touches no version or acceptance |

## Design

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

Guards: `save()` / `delete()` on the instance and `update()` / `delete()` / `bulk_create(update_conflicts=...)` on `TranslationQuerySet`, each naming `Translation` directly; refusals raise `PublishedTranslationError`. `same_wording` moves to a module function used by both models. Indexes: the partial unique on `(version, language)` for the current row serves `live()` and the version page; `Meta.indexes` adds `(version, language, published_at)` for the history and `replaced_at` subquery; `publisher_subject` is indexed, as on `Version`, for the account-removed lookup.

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
- `live_since` property: the later of `published_at` and `version.published_at`; `None` while
  the version is a draft, and when the row was replaced at or before the version's publication.
- `publisher_display` as on `Version`.
- `language_name` from the site's own label in `LANGUAGES`, then `get_language_info`, then the code, and `is_offered` for the admin's flag (FR-015).

`offered_languages()` (module function, read at use): `[]` unless
`settings.is_overridden("LANGUAGES")`; otherwise `settings.LANGUAGES` without the code
`get_supported_language_variant(settings.LANGUAGE_CODE)` resolves to.

`VersionQuerySet.missing_translation(language=None)`: published versions with no live row in
that language, or in any offered language when `None`. One query.

### Exceptions

`TranslationError(Exception)` for a refused create or clean (a language not offered, the main language), and `PublishedTranslationError(Exception)` for a write to a wording once live, in `exceptions.py`. A language dropped from `LANGUAGES` between create and publish is refused at publish with `TranslationError`; `save(update_fields=...)` inside `publish()` skips the check. `save()` calls the language check so `objects.create()` refuses too (US-2).

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
  translation" with one choice per offered language and one for any. The list shows when `offered_languages()` is non-empty or the version has any translation. The filter shows only when a language is offered.
- `VersionAdmin.get_deleted_objects` drops translations from `perms_needed`: discarding a draft version is the version's own permission, and its translations go with it (FR-006).

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

None. `Version` is untouched, and `Translation` repeats the guard pattern rather than sharing a base, because a shared abstract base would not survive into migration state.
