# Decisions — 015 Translations of a published version

## D1 — django-modeltranslation and django-parler are not used

Research N1. Both keep one mutable wording per language. django-modeltranslation also puts it on
the version's own row, which the immutability guard refuses, and needs migrations generated per
site inside the installed package.

**ADR:** none — a package choice recorded in research, nothing downstream inherits it.

## D2 — One model, one row per wording

The rows for one version and one language are that version's translation into the language. The
current row is the live wording and each superseded row an earlier one, kept with the times it was
live, because a person may agree while reading a translation (#156) and G2 requires that what they
saw can be produced later. It mirrors document and version, and reuses their guard and admin
pattern rather than adding a second parent model.

A wording added for a language that already has a translation is a correction of it (FR-003,
approved by the maintainer at the plan review). Two drafts for one language are both kept, as the
spec's edge case on simultaneous corrections requires.

**ADR:** docs/adr/0032-a-translation-keeps-every-wording-it-has-had.md

## D3 — Live is derived, not stored

A translation is live when its row is not a draft and its version is published. One put live on a
pending version therefore goes live with the version, with no hook on `Version.publish()`.

Frozen is wider than live: a wording is frozen from the moment it is put live, whatever its
version's status, because otherwise code could rewrite a wording, or its stored HTML, between being
put live and being served (code review TRN-001). Returning a pending version to draft is the one
sanctioned change, made through the base manager. The test an earlier group wrote asserting the
opposite was inverted with the fix.

**ADR:** docs/adr/0032-a-translation-keeps-every-wording-it-has-had.md

## D4 — No language is offered until the project sets `LANGUAGES`

Django's built-in default lists every language it ships, and no site offers all of them. With no
override, nothing about translations appears. Approved by the maintainer at the plan review.

**ADR:** none — a default documented on the authoring page, local to this feature.

## D5 — `Translation` has its own guard, and `Version` is left alone

A shared abstract base was planned and dropped at design review. Django removes abstract bases from
the models it builds for migrations, so a guard that reaches its frozen fields through the base
would stop refusing writes there, or crash. `Translation`'s guard names `Translation`, as
`Version`'s names `Version` and `Acceptance`'s names `Acceptance`.

**ADR:** none — it applies an existing ADR (0004) to a new model.

## D6 — Indexes on `Translation`

The partial unique on `(version, language)` for the current row serves `live()` and the version
page. A composite `(version, language, published_at)` serves the history and the `replaced_at`
subquery. `publisher_subject` is indexed as on `Version`, for finding what a removed account put
live. `language` gets no index of its own: nothing filters on it without the version.

**ADR:** none — local to this model.

## D7 — Discarding a version takes its translations without their permissions

The admin checks delete permission on everything a delete removes. A translation put live on a
pending version is not deletable by itself, so the version's discard would be refused.
`VersionAdmin` drops translations from that check: discarding a draft or pending version is the
version's own permission (FR-006).

**ADR:** none — local to this admin.

## D8 — A pending state, between draft and published

The maintainer ruled at the plan review that a version is never translated while it is a draft,
and asked for a state that locks its wording while translations are drafted. Pending freezes the
wording and summary, and is otherwise a draft: no number, no standing, invisible to readers,
discardable. Locking and returning need the permission to publish. `published()` and
`is_published` mean current or superseded only, so every reader of them ignores pending.

**ADR:** docs/adr/0031-a-version-can-be-locked-for-translation-before-it-is-published.md

## D9 — A signal for every change of state

The maintainer's instruction at the plan review, so a project can, for instance, translate a
version automatically when it becomes pending. Each is sent after commit with `send_robust`, as
`version_published` is.

**ADR:** none — it applies ADR 0016 to the new changes of state.

## D10 — `Version.same_wording` became a module function

`Translation` needs the same comparison, so it moved to `mvp_compliance.models.same_wording`. No
alias is kept (Article XV); the CHANGELOG records it.

**ADR:** none — a move of one helper.
