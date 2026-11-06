# Tasks — 015 Translations of a published version

Derived from [plan.md](./plan.md). Task ids are stable. Every task that changes behaviour follows
Article I: the failing test comes first. Tests find elements by fixture data, id, address or
`data-` hook, never by wording.

Order: Foundational, US-1, US-2. Documentation is written in the story that introduces the
public name.

## Foundational

- [ ] T001 Extract `FrozenOnPublication` and `FrozenOnPublicationQuerySet` from `Version` / `VersionQuerySet` as planned; `Version` uses them with its own frozen fields and message, manager forwarding unchanged. **Done when:** Full suite green with no test changed; pre-commit green

## User Story 1 — Translating a version, and correcting the translation later (P1, issue #158)

### Group 1 — the model

- [ ] T002 [US1] `tests/settings.py` sets `LANGUAGES` to English, German and French; `tests/factories.py` gains a translation factory. `tests/test_models.py::TestOfferedLanguages` — offered is `LANGUAGES` without the main language; empty when `LANGUAGES` is not overridden; `en-us` main resolves against `en`. **Done when:** Fails before T003
- [ ] T003 [US1] `offered_languages()`. **Done when:** T002 passes
- [ ] T004 [US1] `tests/test_models.py::TestTranslation` — a draft is writable; create and `clean` refuse a language not offered and the main language with `TranslationError`; `publish` stores rendered, sanitised HTML and the publisher; a summary is refused when the version has none; empty output and a wording identical to the current one are refused; publishing a second wording supersedes the first, which keeps every field and gains `replaced_at`; the version's every field and its acceptances are unchanged throughout (FR-007, SC-001); every frozen field is refused on `save()` and on `update()` of a published row, and `delete()` of one is refused on the instance and the queryset (FR-008, SC-003 — each test reinstates the defect by removing a guard and watching it fail); `live()` excludes a current row of a draft version and includes it once the version is published, with `live_since` the version's publication time (FR-006); discarding a draft version removes its translations; removing the publisher's account clears `publisher` and keeps `publisher_subject`, and `publisher_display` says the account was removed; a notice's version is translated like any other (FR-012); two drafts for one version and language are both kept, and the later one put live is the current one. **Done when:** Fails before T005
- [ ] T005 [US1] `Translation`, its queryset and manager, `TranslationError`, migration `0004_translation`. **Done when:** T004 passes; `makemigrations --check` clean; migrate from zero
- [ ] T006 [US1] `tests/test_models.py::TestMissingTranslation` — `Version.objects.missing_translation("de")` lists published versions with no live German row and not drafts; `missing_translation()` covers any offered language; one query. **Done when:** Fails before T007
- [ ] T007 [US1] `VersionQuerySet.missing_translation` and its manager forwarder. **Done when:** T006 passes

### Group 2 — the admin

- [ ] T008 [US1] `tests/test_admin.py::TestTranslationAdmin` — a translation is added only from a version and an offered language, and the add form for an existing translation starts from its current wording; an account holding add/change/view on translations, view on versions and `publish_translation` can add, preview and put live a translation and a correction, and gets 403 on the version's publish view and no change or delete on any version (FR-010, SC-004); without `publish_translation` the translation's publish view is 403; a published translation's page has no editable form and no delete; the preview shows the rendering the publish will store; the summary field is absent when the version has none. **Done when:** Fails before T009
- [ ] T009 [US1] `TranslationForm`, `TranslationAdmin`, its three templates. **Done when:** T008 passes
- [ ] T010 [US1] `tests/test_admin.py::TestVersionTranslations` — a published version's page lists each offered language with its live translation or the lack of one, and links to add or correct (FR-011); a kept translation in a language no longer offered is listed and marked by a `data-` hook (FR-015); the versions list filter narrows to versions missing a translation in one language and in any; with no `LANGUAGES` override, neither the list nor the filter appears; the versions list's query count does not grow with the number of translations (SC-005). **Done when:** Fails before T011
- [ ] T011 [US1] `VersionAdmin` additions as planned. **Done when:** T010 passes
- [ ] T012 [US1] Strings in the English catalogue. Documentation for US-1: `docs/authoring.md` "Translating a version", `docs/models.md` `Translation`, `CONTEXT.md` *Translation*, FS-003 spec's "readings" → "translations", README feature list, `CHANGELOG.md` *Added* with the personal-data line (Article XIV). The demo sets `LANGUAGES` to English and German. **Done when:** Catalogue tests green; docs check green

## User Story 2 — A developer adds translations from code (P3, issue #159)

- [ ] T013 [US2] `tests/test_models.py::TestTranslationFromCode` — create then `publish()` from code gives the same rows as the admin, with nobody named unless an account is passed; a correction from code keeps the earlier wording; a language not offered raises `TranslationError` and writes nothing; publishing an already-published row raises `PublishError` and writes nothing. **Done when:** Passes against T005 (US-1 built the API; this story pins it as public)
- [ ] T014 [US2] Documentation for US-2: `docs/authoring.md` "From code" with a runnable example (a data migration and a plain call), `TranslationError` in the exceptions reference. **Done when:** Docs check green; the example runs in a test
