# Research — 016 Reading a document in your own language

## Assumptions checked

Run on `main` at `14881cf`, 2026-11-10, against the demo seeded with `seed_demo`.

- **The document's page is routed and renders.** `/legal/privacy-policy/` answers 200 with a
  request in German. It serves the version's own stored HTML and not the live German translation,
  as expected before this feature.
- **The agreement page is routed and renders** for a signed-in person: `/legal/agree/` answers 200.
- **Live translations can be read.** `Translation.objects.live()` returns the demo's three: the
  privacy policy 2026.1 in German, and the impressum 2025.1 in German and Spanish. Spanish is not
  in the demo's `LANGUAGES`, so the demo already holds the "language no longer offered" case.
- **A translation keeps what this feature needs to serve and identify it.** `Translation` holds
  `language`, `html` (stored at publication), `summary`, `status`, `published_at` and
  `with_replaced_at()`, so the wording live at a given moment can be found.
- **An acceptance holds nothing about language today.** Its fields are `user`, `subject`, `version`,
  `accepted_at` and `ip_address`.
- **The demo cannot switch language yet.** It sets `LANGUAGES` to English, German and French but
  installs no `LocaleMiddleware`, so every request runs in the main language. The demo needs one
  for this feature to be seen. That is a demo change, not a package one (FR-001).
- **The pages' existing tests pass:** 346 tests selected by document page, agreement and
  translation, all green.
