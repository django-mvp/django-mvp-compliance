# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `Document` and `Version` models for versioned legal text: a document holds
  a lasting name, and each version holds the Markdown wording written for
  it. A version starts as a draft, and publishing renders it to HTML,
  makes it the version in force, and moves the previous one to superseded.
  A published version's wording can never change again.
- Rendering depends on `markdown`, which turns the authored wording into
  HTML, and `nh3`, which sanitises that HTML against an explicit allow list
  before it is stored. The renderer used is configurable with one setting,
  `MVP_COMPLIANCE_RENDERER`, a dotted path to a renderer class, defaulting
  to the one this package ships.
- `Document` and `Version` registered in the Django admin, so a compliance
  editor can write a version without a developer. The `markdown` field uses
  a formatting-control editor — headings, bold, italics, lists, links and
  block quotes, and nothing else — over an ordinary textarea, built on
  [EasyMDE](https://github.com/Ionaru/easy-markdown-editor), vendored into
  the package with its own icons. Stored content is ordinary Markdown either
  way, and every control the toolbar offers survives publication intact.
- A draft is reachable in the admin only by someone holding `view_version`
  and `change_version`, and the package still serves no address a visitor
  can reach directly. Deleting a version needs `delete_version` and is
  refused once that version has been published, matching what the model
  layer already refuses.
- A Preview link on a version's change page shows the rendering the
  published page will actually use, distinct from the toolbar's own
  inline display: a fresh rendering for a draft, and the HTML stored at
  publication for a published version, never rendered again. Content the
  sanitiser's allow list strips previews as stripped, so the loss is
  visible before publication.
