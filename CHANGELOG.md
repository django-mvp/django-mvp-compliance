# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `render_publication_email(version, replaced, site_url)`, in `mvp_compliance.emails`, which
  writes the subject and plain-text body of an email announcing a publication and returns them.
  It sends nothing. The subject is always one line, the text is translatable, and a template at
  the same path in a project replaces the package's. See [docs/announcing.md](docs/announcing.md).
- A `version_published` signal, in `mvp_compliance.signals`, sent once each time a version is
  published and after the publication commits. It carries the version, the account that published
  it and the version it superseded. It is not sent for a refused or rolled-back publication, and a
  receiver that raises is logged on `django.dispatch` and cannot undo the publication. The admin
  publish page now shows a success message after every successful publication. See
  [docs/announcing.md](docs/announcing.md).
- Each published version now records the account that published it: its
  primary key, kept as text next to a link to the account. This is new
  personal data held about a person. It is written once, when the version is
  published, and cannot be changed afterwards. Removing the account clears the
  link, keeps the identifier, and leaves the version standing. The admin
  publish page records the signed-in user, and **Published by** appears next
  to **Published at** on the version page and in the version and document lists.
  A version published before this change shows "Unknown publisher".
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
- Publishing is a distinct action behind its own permission,
  `publish_version`, held separately from the permissions writing a draft
  needs. A version's change page offers a Publish link, which leads to a
  confirmation page naming the document and version, showing the
  rendering about to go live, and stating plainly that the wording cannot
  be changed afterwards and that a correction is published as another
  version. Publishing happens only when that page is posted. Both
  refusals `Version.publish()` can raise reach the author as a readable
  message rather than an error page. A published version's change page
  offers no editable form at all — Django serves its own read-only page
  in its place.
- A version that is currently in force offers a Start the next version
  link on its own change page, which opens the version add form with its
  document chosen and that version's Markdown already in the box. A
  document with nothing published yet opens the box empty. The version
  the wording came from is never opened for writing.
- A document's change page offers View current version, leading to the
  version in force when one exists, and Version history, leading to the
  versions list narrowed to that document. The versions list can be
  narrowed to one document from its own filter sidebar too.
- The documents list shows, beside each name, the version in force
  (linked to its own page, or a plain statement that nothing is in force
  yet), how long it has been in force, and how many versions have been
  published — current and superseded together, a draft never counted.
  The list costs the same number of queries at any number of documents.
- A version can only be added from a document: the versions list offers
  no add control, and a request for the add form that names none is
  refused, whatever permissions it carries.
- Saving a next version whose wording says exactly what the version in
  force already says is refused, with a message saying so. A document's
  first version is never refused this way — there is nothing published
  yet to compare it against.
- The Markdown editor fills the width available to it, at any window
  width, instead of sitting in a narrow column.
- `Acceptance`, the record that one user agreed to one published version, at
  one moment: `Acceptance.objects.record(user, version)`. It names the
  user, the version and when it happened, is refused against a version
  that has never been published, and is never editable or deletable once
  written — every route that could change or delete one, including
  through the queryset and inside a migration, raises instead. Recording
  the same person's acceptance of the same version again, including two
  attempts racing each other, returns the record that already exists
  rather than writing a second one.
- `Document.objects.outstanding_for(user)` and
  `document.is_outstanding_for(user)` answer which documents a person has
  not accepted the version in force of, in one query regardless of how
  many documents exist, so the question is cheap enough to ask on an
  ordinary page.
- Removing an account leaves that person's acceptances in place by
  default — closing an account is not a statement about the evidence, and
  `Acceptance.objects.for_person(user)` /
  `Acceptance.objects.for_subject(subject)` still find them by the
  identifier that survives the account's removal. A project bound by a
  stricter erasure requirement sets
  `MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL = False`, and
  removing an account then takes that person's acceptances with it.
  Either way, removing one account never touches anyone else's records.
  The surviving identifier is the removed account's primary key, and this
  package holds nothing else that identifies anybody once an account is
  gone, so a project keeping acceptances past removal has to keep its own
  map from the person to that identifier. `docs/models.md` shows the
  receiver that writes one.
- By default an acceptance holds nothing about the person beyond who they
  are, which version, and when. A project that turns
  `MVP_COMPLIANCE_RECORD_IP_ADDRESS` on also gets the IP address the
  request came from, provided the request is passed to `record()` —
  personal data about someone who did not ask for it to be kept, so it is
  held only when a project has deliberately chosen to hold it. Turning
  the setting on or off only ever affects acceptances recorded
  afterwards; an existing record keeps whatever it held when it was
  written.
- `mvp_compliance.records.produce(subject)` assembles everything this
  package holds about one person into a single answer: every acceptance,
  each carrying the wording it was actually served, in one query
  regardless of how many documents exist. An answer for somebody the
  package holds nothing about says so, and carries the same statement of
  what it covers as any other answer.
- The admin's **Everything held about a person** page, at
  `/admin/mvp_compliance/disclosure/`, is the one way to reach that
  answer: a GET behind its own permission, `produce_disclosure`, which
  nobody holds by default and which every other permission this package
  defines grants nothing towards. Every refusal — not signed in, signed
  in without the permission, or asking about somebody with no records —
  looks the same. The page states plainly what it covers and what it
  does not, in both states, and offers no download and no management
  command.
- `mvp_compliance.records.resolve_subject(text)` finds the person a
  request names: an account's login name, then its email address where
  the user model has one, and otherwise the identifier itself — which is
  what makes it possible to ask about somebody whose account is gone,
  because their acceptances still carry it.
- Producing an answer reads what is already held and nothing more.
  Nothing about the request is stored, and asking twice leaves no
  record of having asked once.
- Django 6.1 is supported, and tested on every change alongside 5.2 and 6.0.

### Changed

- A version is numbered when it is published instead of when its draft is created, and the number
  is the year of publication and its place among the document's versions published that year,
  such as `2026.2`. The count starts again each year, using the site's time zone. A draft has no
  number, so drafts that are never published leave no gaps. `Version.number` is now a string, or
  `None` for a draft, and versions are ordered by when they were published, with drafts last. The
  admin shows "Draft" where a draft's number would be. Existing published versions keep the number
  they were published under, and migration `0006` clears the number from existing drafts.
- The package is built with hatchling instead of poetry-core, and developed with uv instead of
  Poetry. The wheel contains the same files as before. The source distribution does too, plus the
  repository's `.gitignore`, which hatchling includes so that a build from it leaves out the same
  files.
