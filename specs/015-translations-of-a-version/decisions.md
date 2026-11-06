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
