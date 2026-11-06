# Decisions — 015 Translations of a published version

Ambiguities resolved while specifying, each open to the maintainer's veto at the spec gate.

- **The site's own `LANGUAGES` and `LANGUAGE_CODE` decide the languages.** The package keeps no list.
  A version's own text is taken to be in the main language, and a translation into it is refused.
- **A correction keeps the wording it replaces.** A person may agree while reading a translation
  (#156), and G2 requires that what they saw can be produced later. Overwriting a live translation
  would break that while leaving the version untouched.
- **A translation goes live through the same preview-then-publish step as a version**, and its HTML
  is stored when it goes live (Article XII).
- **Translations of a draft go live with the version**, so a version and its translations can launch
  together. Discarding the draft discards them.
- **A new version starts with no translations.** Its wording differs from the one it replaces.
- **Translating is a permission of its own.** A translator is often an outside agency, not the
  person who decides the wording.
- **The admin shows which published versions lack a translation into each offered language**, so a
  gap is seen by the editor rather than found by a reader.
- **Translations can be added from code** (US-2, P3), matching publishing a version from code.
- **Wording outside this directory is left for the build.** The record-of-acceptance spec (003) says
  "R7 adds readings of a version"; the build changes it to "translations", and adds *Translation* to
  `CONTEXT.md`, in this same pull request.

## D1 — django-modeltranslation and django-parler are not used

Research N1. Both keep one mutable wording per language. django-modeltranslation also puts it on
the version's own row, which the immutability guard refuses, and needs migrations generated per
site inside the installed package.

## D2 — One model, one row per wording

The rows for one version and one language are that version's translation into the language. The
current row is the live wording and each superseded row an earlier one. It mirrors document and
version, and reuses their guard and admin pattern rather than adding a second parent model.

The spec's refusal of "a second translation in the same language" (US-1 scenario 11, US-2
scenario 3) is met by construction: there is no separate translation row to duplicate, so a
wording added for a language that already has one is always a correction of that translation.
Two drafts for one language are both kept, as the spec's edge case on simultaneous corrections
requires.

## D3 — Live is derived, not stored

A translation is live when its row is current and its version is published. One put live on a
draft version therefore goes live with the version, with no hook on `Version.publish()`.

## D4 — No language is offered until the project sets `LANGUAGES`

Django's built-in default lists every language it ships, and no site offers all of them. With no
override, nothing about translations appears.

## D5 — The frozen-field guard is shared by `Version` and `Translation`

Extracted into a base rather than copied, so the rule that a published wording never changes is
enforced by one piece of code.
