# Plan — 015 Translations of a published version

Spec: [spec.md](./spec.md) · Research: [research.md](./research.md) · Tasks: [tasks.md](./tasks.md)

## Summary

Two changes. `Version` gains a **pending** state between draft and published, with actions to lock
a draft for translation and to return a pending version to draft. A new model, `Translation`, holds
one row per wording of a pending or published version in one language, reusing the guard,
rendering, publisher and admin patterns `Version` already has. Every change of state of either
sends a signal after it commits. No reader-facing page changes.

## Technical context

Python 3.12+, Django 5.2 / 6.0 / 6.1, uv. No new dependency (research N1). One migration,
`0004_pending_and_translation`: alters `Version.status`'s choices, replaces the check constraint
`version_status_agrees_with_its_publication` with one that accepts `pending`, and creates the
`Translation` table. No row is rewritten (Article XV).

## Constitution check

| Article | How it holds |
|---|---|
| I (test first) | Every behaviour task in `tasks.md` is preceded by its failing test |
| VIII (i18n) | Every new string marked. `makemessages` over the package stays clean |
| XI (immutability) | A pending version's wording and summary are guarded by the same code that guards a published one. A translation's wording, once live, is guarded on the instance and the queryset by its own guard naming `Translation`, as `VersionQuerySet` names `Version` (ADR 0004) |
| XII (stored HTML) | A version's HTML is still rendered at publication, never at locking. A translation's is rendered once, when it is put live |
| XIII (no claim) | No string says a translation governs or is equivalent |
| XIV (personal data) | `publisher` + `publisher_subject` on `Translation`, with `help_text`, and a CHANGELOG entry naming them. Signals pass accounts to project receivers, as `version_published` does |
| XV (stored data) | The migration adds a choice, widens a constraint and creates a table. No version or acceptance is changed |

## Design

### The pending state — `Version`

- `Version.Status.PENDING = "pending"`. The check constraint's unpublished branch becomes
  `status__in=["draft", "pending"]` with the same empty number, `published_at`, `html`, publisher
  and subject.
- **Published means current or superseded, and nothing else.** `VersionQuerySet.published()`
  becomes `filter(status__in=[CURRENT, SUPERSEDED])`, `is_published` becomes the same test, and
  every call site that reads "not a draft" as "published" is converted (admin.py:64, :205, :211,
  :292; models.py:609, :1020, :1063; any template test of `status == "draft"`). `drafts()` keeps
  meaning draft only. New `pending()`. Every page, query and check that ignores drafts must ignore
  pending versions (FR-021, SC-007).
- **The guard has two frozen sets.** `PUBLISHED_FROZEN_FIELDS` stays. `PENDING_FROZEN_FIELDS =
  ("document", "markdown", "summary")`. `refuse_if_published_wording_changed` and
  `VersionQuerySet.update()` refuse a change to the pending set on a pending row, and to the
  published set on a published row. `delete()` is allowed for a draft or pending row.
- `lock_for_translation(by=None)`: draft → pending under `select_for_update()` on the document,
  rechecking the stored status. Refused with `PublishError` on anything but a draft, and on the
  checks `publish()` makes that the locked wording would fail: empty output, or the same wording as
  the version in force.
- `return_to_draft(by=None)`: pending → draft, under the same lock. Every non-draft `Translation`
  row of the version returns to draft in the same transaction, `html`, `published_at`, publisher
  and subject cleared, wording kept. Refused with `PublishError` on anything but pending.
- `publish()` accepts a draft or a pending version. Nothing else about it changes.

### `Translation`

Fields: `version` (FK `Version`, `CASCADE`, `related_name="translations"`), `language`
(`CharField(max_length=15)`, no `choices`), `markdown`, `summary` (blank), `html`, `status`
(draft · current · superseded), `published_at`, `publisher` (FK user, `SET_NULL`),
`publisher_subject`. `verbose_name` and `help_text` on every field. Frozen once **live**, meaning
the row is not a draft and its version is published: `version`, `language`, `markdown`, `summary`,
`html`, `published_at`, `publisher`, `publisher_subject`. A put-live row of a pending version is
not yet live, so `return_to_draft` can return it through the ordinary queryset.

Guards: `save()` / `delete()` on the instance and `update()` / `delete()` /
`bulk_create(update_conflicts=...)` on `TranslationQuerySet`, each naming `Translation` directly;
refusals raise `PublishedTranslationError`. `same_wording` moves to a module function used by both
models.

Constraints and indexes: one current row per `(version, language)` (partial unique), which serves
`live()` and the version page; `Meta.indexes` adds `(version, language, published_at)` for the
history and `replaced_at` subquery; `publisher_subject` indexed as on `Version`; a check constraint
tying status to `published_at` / `html`. Meta permission `("publish_translation", "Can put a
translation live")`.

Manager `TranslationManager` (explicit forwarding, `use_in_migrations`). Queryset adds `live()`
(current and version published) and `with_replaced_at()`.

Methods:

- `save()` refuses with `TranslationError` a version that is a draft, a language not offered
  (`offered_languages()`), and the main language. `save(update_fields=...)` inside `publish()`
  skips the language check.
- `publish(publisher=None)` refuses with `PublishError`: a row that is no longer a draft (rechecked
  under `select_for_update()` on the version row), a version that is a draft, a language no longer
  offered, a translated summary when the version has none, output that renders empty, and a
  wording whose markdown and summary both match the current one for the same version and language.
  It supersedes that current row, renders and stores `html`, sets `published_at`, `publisher`,
  `publisher_subject`, in one transaction.
- `live_since`: the later of `published_at` and `version.published_at`; `None` while the version
  is pending, and when the row was replaced at or before the version's publication.
- `publisher_display` as on `Version`. `language_name` from the site's own label in `LANGUAGES`,
  then `get_language_info`, then the code. `is_offered` for the admin's flag (FR-015).

`offered_languages()` (module function, read at use): `[]` unless
`settings.is_overridden("LANGUAGES")`; otherwise `settings.LANGUAGES` without the code
`get_supported_language_variant(settings.LANGUAGE_CODE)` resolves to.

`VersionQuerySet.missing_translation(language=None)`: pending or published versions with no
current translation row in that language, or in any offered language when `None`. One query.

### Signals — `mvp_compliance/signals.py`

All sent with `send_robust` from `transaction.on_commit` registered last inside the changing
transaction, exactly as `version_published` is (ADR 0016), so a refusal or rollback sends nothing
and a raising receiver undoes nothing.

| Signal | Sender | Arguments |
|---|---|---|
| `version_pending` | `Version` | `version`, `by` |
| `version_returned_to_draft` | `Version` | `version`, `by` |
| `version_published` | `Version` | unchanged: `version`, `publisher`, `replaced` |
| `translation_published` | `Translation` | `translation`, `publisher`, `replaced` |
| `translation_returned_to_draft` | `Translation` | `translation`, `by`, sent once per row `return_to_draft` returns |

Superseding is reported by the `replaced` argument of the publication that caused it.

### Exceptions

`TranslationError(Exception)` for a refused create (a draft version, a language not offered, the
main language), and `PublishedTranslationError(Exception)` for a write to a live wording, in
`exceptions.py`. Locking and returning reuse `PublishError`.

### Admin — `mvp_compliance/admin.py`

- `VersionAdmin`: a pending version has no editable form (as a published one). Its page offers
  Publish, Return to draft and Delete; a draft's page offers Lock for translation beside Publish.
  Lock and return are confirmation views checking `publish_version`, on the publish view's
  pattern. `has_delete_permission` allows draft and pending. `get_deleted_objects` drops
  translations from `perms_needed`: discarding is the version's own permission, and its
  translations go with it (FR-006).
- `VersionAdmin` also gets a read-only `translations` field on a pending or published version's
  page, listing each offered language with its live or put-live translation (link), a link to add
  one, or to correct it, plus any kept translation in a language no longer offered, flagged. The
  list shows when `offered_languages()` is non-empty or the version has any translation. A list
  filter "Missing a translation", one choice per offered language and one for any, shown only when
  a language is offered.
- `TranslationForm`: `markdown` (editor widget), `summary`, plus `version` and `language` as hidden
  fields on add, with `language` a `ChoiceField` built from `offered_languages()` at request time.
  `summary` absent when the version has none.
- `TranslationAdmin`, on the `VersionAdmin` pattern: added only from a pending or published version
  (`?version=&language=`); adding a wording for a language that already has a translation starts
  from its current wording and is labelled a correction; non-draft rows read-only; preview and
  publish-confirmation views, the publish view checking `publish_translation` only; list shows
  version, language, status, live since, put live by; filters by language and status.

### Docs

`docs/authoring.md` gains "Locking a version for translation" and "Translating a version" (what
governs, permissions, correcting, from code). `docs/models.md` documents the pending state and
`Translation`. `docs/announcing.md` lists every signal. `CONTEXT.md` gains *Pending*, *Translation*
and *Live* (a translation's current wording once its version is published, not a synonym for
published). FS-003 spec's "readings" becomes "translations". README feature list, `CHANGELOG.md`
*Added* and *Changed* (`published()` and `is_published` no longer include a pending version, which
did not exist before) with the Article XIV line.

## Project structure

```
mvp_compliance/models.py           pending state, Translation, offered_languages, missing_translation
mvp_compliance/signals.py          four new signals
mvp_compliance/exceptions.py       TranslationError, PublishedTranslationError
mvp_compliance/forms.py            TranslationForm
mvp_compliance/admin.py            TranslationAdmin, VersionAdmin additions
mvp_compliance/migrations/0004_pending_and_translation.py
mvp_compliance/templates/admin/mvp_compliance/{version,translation}/*.html
tests/test_models.py, test_admin.py, test_forms.py, test_views.py, test_signals.py,
tests/conftest.py, tests/factories.py
docs/authoring.md, docs/models.md, docs/announcing.md, CONTEXT.md, README.md, CHANGELOG.md,
specs/003-*/spec.md
```

## Complexity tracking

None. `Translation` repeats the guard pattern rather than sharing a base with `Version`, because a
shared abstract base would not survive into migration state.
