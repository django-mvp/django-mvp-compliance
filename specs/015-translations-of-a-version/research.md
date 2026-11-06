# Research — 015 Translations of a published version

Read against `main` at 2026-11-06 (FS-001 to FS-014 delivered).

## Planning notes

### N1 — "Django-model-translations" (`django-modeltranslation`)

**Not adopted.** `django-modeltranslation` 0.19 registers a model's fields for translation
and adds one database column per field per language (`markdown_de`, `html_de`, …) to that
model's own table. Three things rule it out here:

- **The columns would sit on `Version`'s own row.** Writing a translation would then be an
  update to a published version, which `VersionQuerySet.update()` and `Version.save()` refuse
  (Article XI, FR-007). Exempting the new columns from the guard would leave the one table the
  package exists to protect partly mutable.
- **One column per language keeps one wording.** A correction would overwrite it, and FR-008
  requires every wording that has been live to be kept with the times it was live.
- **The columns depend on the host's `LANGUAGES`.** Its own documentation has a project run
  `makemigrations` for the registered app whenever a language is added. For a reusable package
  that means migrations generated inside an installed package, different on every site, and
  never shipped. Article XV makes stored data the one thing the package's migrations must
  carry forward exactly.

`django-parler` was looked at for the same reason (a separate translations table, one row per
object and language). It keeps one mutable row per language and has no drafts, no stored
rendering and no history, so it solves the part of this feature that is easy and none of the
part that is not. Not adopted either.

## Approach

A translation is shaped exactly like the thing it translates. The package already has the
machinery a translation needs, for `Version`: drafts, a preview, publication behind its own
permission, stored HTML rendered once (Article XII), a frozen set of fields guarded on the
instance and on the queryset, a publisher kept as account and subject. One new model reuses
all of it.

- **`Translation`**: one row per wording. `version` (FK), `language` (code), `markdown`,
  `summary`, `html`, `status` (draft · current · superseded), `published_at`, `publisher`,
  `publisher_subject`. The rows for one version and one language *are* that version's
  translation into the language; the current row is its live wording, and each superseded row
  an earlier wording, with the time it went live and (annotated, as for versions) the time the
  next one replaced it. A correction is a new draft row for the same version and language,
  put live the same way.
- **Live** means a current row whose version is published. A translation put live while its
  version is a draft therefore goes live with the version, by definition, with no hook on
  `Version.publish()` (FR-006).
- **Languages** are read at use, never stored as `choices`, so a change to `LANGUAGES` never
  creates a migration. Offered = `settings.LANGUAGES` minus the main language
  (`get_supported_language_variant(LANGUAGE_CODE)`), and nothing at all when the project has
  not set `LANGUAGES` (`settings.is_overridden("LANGUAGES")`): Django's built-in default lists
  every language it ships, which no site offers.
- **Permission**: `publish_translation` on `Translation`, checked by its own publish view and
  by nothing else. Writing drafts uses the model's ordinary add/change permissions. Neither
  touches `Version`'s permissions (FR-010).
- **From code**: `Translation.objects.create(...)` then `translation.publish(publisher=None)`,
  the same pair a version offers. Refusals raise `TranslationError` (new, ADR 0003).
- **Admin**: a `TranslationAdmin` modelled on `VersionAdmin` (add only from a version, preview,
  publish confirmation, published rows read-only). A version's page lists the offered languages
  with the live translation in each, or the lack of one, and links to add or correct. The
  versions list gets a filter for versions missing a translation.

## Unknowns settled

- **Discarding a draft version** removes its translations by `on_delete=CASCADE`. The
  collector deletes through a raw query, past `TranslationQuerySet.delete()`. That is only
  reachable for a draft version, because a published one cannot be deleted
  (`Version.delete()`, `VersionQuerySet.delete()`, `on_delete=PROTECT` from `Acceptance`).
- **Account removal** clears `Translation.publisher` through `SET_NULL`, a raw update past the
  queryset guard, exactly as for `Version.publisher` (no `Meta.base_manager_name`).
- **A translated summary** is refused at publication when the version has none.
- **Two corrections at once** are two drafts. Both are kept. Putting one live supersedes the
  wording in force under a lock on the version row, as `Version.publish()` locks the document.

## What already exists

| New piece | Found at | Use |
|---|---|---|
| Frozen-field guard (instance + queryset) | this repo: `Version.save`, `stored_row`, `refuse_if_published_wording_changed`, `VersionQuerySet.update/delete` | Extracted into a shared base used by both models, not copied |
| Rendering + sanitising | this repo: `rendering.get_renderer()` | Reused as is |
| Publisher as account + subject, "Account removed" | this repo: `Version.publisher*`, `Acceptance.subject_of` | Same fields, same display |
| `replaced_at` annotation | this repo: `VersionQuerySet.with_replaced_at` | Same subquery shape, keyed on version + language |
| Preview / publish confirmation admin pages | this repo: `VersionAdmin.preview_view/publish_view` and templates | Same pattern; templates reused where they take only `html` |
| Markdown editor widget | this repo: `widgets.MarkdownEditorWidget` | Reused |
| Language list and names | Django: `settings.LANGUAGES`, `get_language_info`, `get_supported_language_variant` | Reused |
| History of wordings | nothing installed does it (see N1) | New code: rows on `Translation` |
| Admin list filter | Django: `admin.SimpleListFilter` | Reused |
