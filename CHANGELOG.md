# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `MVP_COMPLIANCE_DOCUMENTS`, a setting that declares the documents a site links to, by slug and
  name. `migrate` creates each declared document that does not exist yet, with no version, so its
  address can be linked in every environment before anything is published. Declared documents exist in test databases too, so a test or
  fixture that creates a document under a declared slug or name has to fetch it instead. An
  existing document is
  never changed, and a declaration the admin would refuse, or whose name belongs to another
  document, stops `migrate` with `ImproperlyConfigured`. A declared document's slug is fixed from
  the start: `save()`, `update()`, `bulk_update()` and the admin refuse a change to it, with the
  new `DeclaredDocumentError`, until the declaration is removed. See
  [docs/models.md](docs/models.md#declaring-documents) and
  [when the slug is fixed](docs/models.md#when-the-slug-is-fixed).

### Changed

- **Breaking:** django-mvp 0.30 or later is required. To upgrade, list `"daisy_cotton"` directly
  below `"mvp"` in `INSTALLED_APPS`, use `"mvp_forms"` for form rendering, and add
  `"django_filters"`. django-mvp's own changelog lists everything else that changed between
  releases.
- The list of documents on a document page is django-mvp's side panel. On a wide screen it is a
  column on the left that sticks under the header while the document scrolls. On a narrow screen
  it is a drawer, opened by a "Documents" button next to the version switcher. The document page
  now fills the `page.side`, `page.actions` and `page.content` blocks of `page_view.html`, so a
  project template that extends it can override any one of them. It no longer fills `styles` or
  `page.content-wrapper`.
- The alerts the package draws pass their icon, because daisy-cotton 0.2 no longer picks one from
  the alert's variant.

### Removed

- **Breaking:** `mvp_compliance/pages.css` and its `--mvp-compliance-header-clearance` property.
  The panel follows the header's measured height, which django-mvp publishes as
  `--mvp-header-height`. A project that set the clearance can delete that rule.

## [v0.2.0] - 2026-10-13

### Added

- `mvp_compliance.middleware.AgreementMiddleware`, which switches the agreement check on for the
  whole site. Listed in `MIDDLEWARE` after `AuthenticationMiddleware`, it sends a signed-in person
  who has not accepted the current version of an enforced document to the page that asks, from any
  address, with the address they wanted as `next`. A visitor who is not signed in is never touched,
  and nothing happens until the middleware is listed. The page that asks, the package's own pages,
  the sign-out addresses `account_logout`, `logout` and `admin:logout`, and files beneath
  `STATIC_URL` and `MEDIA_URL` stay reachable with no configuration. A submission is redirected
  with no `next`, and an htmx request is answered with an `HX-Redirect` header so the page loads
  whole. A person found to have nothing outstanding is not asked about again for sixty seconds.
  See [docs/enforcement.md](docs/enforcement.md).
- System checks `mvp_compliance.E001`, when the middleware is listed and the page that asks has no
  address, and `mvp_compliance.E002`, when nothing that identifies the signed-in user comes before
  it.
- `MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS`, a list of paths that stay reachable for a person the
  agreement check is stopping. An entry covers itself and every address beneath it, a path segment
  at a time, so `/help/` covers `/help/faq/` and not `/helpful/`. The addresses that are always
  reachable need no entry, and an entry of `/` covers every address. System check
  `mvp_compliance.E003` reports the setting when it is a string. See
  [docs/enforcement.md](docs/enforcement.md#keeping-your-own-addresses-reachable).
- `MVP_COMPLIANCE_AGREEMENT_CHECK_INTERVAL`, the number of seconds a person found to have nothing
  enforced outstanding is not asked about again, `60` when unset. It is read on every request, so
  shortening it takes effect at once, even for a finding made under a longer value. With `0` every
  request is checked against the database and nothing is written to the session. System check
  `mvp_compliance.E004` reports a value that is not a number. See
  [docs/enforcement.md](docs/enforcement.md#the-delay).
- `MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS`, a list of the values accounts sign in with, compared
  with `user.get_username()`. An account named in it is never stopped by the agreement check, and
  a name that matches no account changes nothing. System check `mvp_compliance.E003` reports the
  setting when it is a string, as it does `MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS`.
- The permission `mvp_compliance.skip_agreement`, on `Document`. An account that holds it,
  directly or through a group, is never stopped by the agreement check, and a superuser always is
  let past. It is asked only of a person who is outstanding and about to be stopped, and the answer
  is not remembered, so taking it away takes effect on the next request. Letting an account past by
  either way records no acceptance and changes nothing outstanding for it. It is added by
  migration `0002`, which is still the only migration this release adds. See
  [docs/enforcement.md](docs/enforcement.md#letting-accounts-past).
- `Document.enforced`, which says whether a person who has not accepted a document can be stopped
  until they do. A document created without a choice is enforced, and so is every document that
  existed before the migration. It is changed with an ordinary save or update at any time and
  touches no version and no acceptance. `Document.objects.enforced_outstanding_for(user)` narrows
  `outstanding_for(user)` to the enforced documents, and `outstanding_for()` is unchanged. The
  field is on a document's form and in the documents list in the admin. Migration `0002` adds the
  column and writes nothing else. See [docs/models.md](docs/models.md#enforcement).
- A page that asks a signed-in person to agree to what is outstanding for them, at
  `<prefix>/agree/` (`mvp_compliance:agree`). It lists each outstanding document with its version
  in force, a link to that version's page and a toggle, and a submission records an acceptance of
  each version agreed to, then sends the person to `next` when it is on the same site, otherwise
  to `/`. Opening the page records nothing, a visitor who is not signed in is sent to sign in and
  back, and the page stops nobody. See [docs/pages.md](docs/pages.md).
- `MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL`, the address a person is sent on to from the page that
  asks when no usable `next` was given. It is a path or the name of a URL, and `/` when unset. A
  `next` that is the page's own address is replaced by it too. A signed-in person with nothing
  outstanding who opens the page is now redirected to their destination at once, and the page is
  not drawn. See [docs/pages.md](docs/pages.md#sending-a-person-to-the-page).
- A project replaces the page that asks by placing a template at `mvp_compliance/agreement.html`,
  and changes how an agreement is stored by overriding `AgreementView.record_agreed()`. See
  [docs/pages.md](docs/pages.md#replacing-the-page-that-asks).
- `Acceptance.objects.record_many(user, versions, request=None)`, which records a batch of
  acceptances in one write. It sends no save signals, where `record()` does, and needs a database
  that can ignore conflicts, which rules out Oracle. See [docs/models.md](docs/models.md).

### Changed

- **Breaking: the package needs django-mvp 0.28.1 or later.** It was 0.25.0. django-mvp 0.26 to
  0.28 moved its forms to django-mvp-forms, took its basic components from daisy-cotton and put
  its own components under an `mvp.` prefix, and this package's templates now use those names.
  A project on an older django-mvp cannot install this release. Follow the upgrade notes in
  [django-mvp's changelog](https://github.com/django-mvp/django-mvp/blob/main/CHANGELOG.md)
  for the settings a project changes, which are `"mvp_forms"` in place of `"crispy_tailwind"`,
  the `daisyui` crispy template pack and `"daisy_cotton"` below `"mvp"` in `INSTALLED_APPS`.
  Nothing in this package's own settings, addresses or models changes.
- A project template that replaces one of this package's templates, and was copied from it,
  uses component names django-mvp no longer has. `<c-page>`, `<c-page.title>`,
  `<c-page.content>`, `<c-page.list.empty>`, `<c-card>`, `<c-form>` and `<c-dropdown>` are now
  `<c-mvp.page>`, `<c-mvp.page.title>`, `<c-mvp.page.content>`, `<c-mvp.page.list.empty>`,
  `<c-mvp.card>`, `<c-mvp.form>` and `<c-mvp.dropdown>`. `<c-form.field>` no longer exists.
- On the page that asks, each toggle is drawn by daisy-cotton's `<c-form.label>` and
  `<c-form.toggle>`. The input keeps its name, value, id and `data-required`, and now also has
  `role="switch"`. The words "I agree" are no longer wrapped in a `<span>`.
- The page that asks follows each document's `enforced` field. A document that is not enforced is
  still listed, and is marked optional where it was marked required. After a submission a person is
  sent on once no enforced document is outstanding for them, whatever they left alone among the
  rest, and is shown the page again while one is. A signed-in person with no enforced document
  outstanding who opens the page with a `next` parameter, whatever its value, is redirected at
  once and shown nothing, to `next` when it can be followed and otherwise to the default
  destination. With no `next` they are shown the page and can accept those documents. The page
  behaves as before on a site where every document is enforced, which is every site until a
  document's `enforced` is switched off.
- `AgreementView.is_optional()` returns `not document.enforced` where it returned `False`. A
  project that overrides it may make a document that is not enforced required, and must not make
  an enforced one optional on a site that has listed `AgreementMiddleware`: the middleware asks
  `Document.objects.enforced_outstanding_for()` and never the view, so the two would send a
  person round in a loop. See [docs/pages.md](docs/pages.md#deciding-which-documents-are-required).
- The slug `agree` is no longer available to a document, because it is the address of the page
  that asks a person to agree. The admin and `full_clean()` refuse it, through
  `Document.RESERVED_SLUGS`. A document already published under `agree` stops being reachable at
  its page: the address shows the page that asks. See [docs/models.md](docs/models.md).

## [v0.1.0] - 2026-10-09

### Added

- A page in django-mvp's account area, at `<prefix>/agreed/` (`mvp_compliance:agreed`), where a
  signed-in person sees the documents they agreed to: for each, the versions they accepted, newest
  published first, the day they accepted each, and a link to read that version as it was published.
  Three versions are shown and the rest fold under a count when a document has more than four. It
  shows only the signed-in person's own records and nothing else, answers `GET` and `HEAD` only and
  writes nothing. The package adds one entry, "Agreements", to the account area's menu, and nothing
  to your own `AppMenu` or `MobileFooterMenu`. Mount django-mvp's URLs as well as the package's for
  the page to appear. A project without django-mvp's URLs has no account area: the address answers
  "not found" for everyone and the document pages keep working. A project without the package's
  URLs gets no entry in the account area's menu and nothing fails. When the version in force of a listed document is one the person has not
  accepted, its card says so and links to the document's page. `AcceptanceQuerySet.of_agreed_documents()`
  and the same method on the manager return the acceptances the page lists.
  `django-flex-menus>=0.4.5` is now a dependency.
  See [docs/pages.md](docs/pages.md) and [docs/models.md](docs/models.md).
- Notices: `Document.kind` is `Document.Kind.AGREED` by default or `Document.Kind.NOTICE`, for a
  document such as an impressum that is published to be read and never accepted. A notice is never
  outstanding, recording an acceptance of one of its versions is refused with `RecordError`, and
  its page never says the reader agreed to it. The kind shows in the admin's documents list and can
  be changed at any time without touching a version or a recorded acceptance. See
  [docs/models.md](docs/models.md) and [docs/authoring.md](docs/authoring.md).
- One canonical page for each document that has a version in force, served at an address that
  never changes: `path("legal/", include("mvp_compliance.urls"))` in your URLs, then
  `{% url 'mvp_compliance:document' 'privacy-policy' %}` in a template. Anyone can read it,
  signed in or not, and it renders inside the django-mvp shell. The same address with
  `?version=<number>` shows that published version, current or superseded, for as long as it
  stays published. A document with nothing published, a slug that names nothing, or a
  `?version=` value that is not a published version of the document, answers "not found". A
  superseded version's page carries one alert row with the dates it was in force and a "View
  current version" button. Every document page also carries a version switcher among its
  actions, listing every published version newest first and marking the one shown. Beside the
  wording, every document page lists every document that has a version in force, alphabetically,
  with the one shown marked; below the large breakpoint the list stacks above the wording. The package
  adds nothing to your menus, and every page's breadcrumbs are the document's name alone. See
  [docs/pages.md](docs/pages.md).
- `Document.slug`, a unique slug that forms the document's address, and
  `Document.objects.in_force()`, which returns the documents that have a current version with
  that version already fetched. See [docs/models.md](docs/models.md).
- The slug is validated as lowercase letters, digits and single hyphens, and is fixed once a
  version of the document is published: changing it through `save()`, `update()` or
  `bulk_update()` raises `PublishedVersionError`. The admin suggests the slug from the name and
  shows it read-only once it is fixed. A project restyles a page by placing a template at the
  same path. See [docs/models.md](docs/models.md), [docs/authoring.md](docs/authoring.md) and
  [docs/pages.md](docs/pages.md).
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

- The package ships one migration, `0001_initial`, which creates the whole schema. The nine
  migrations written before the first release are gone. A database migrated from a development
  checkout holds the same tables, so it needs no schema change: delete the `mvp_compliance` rows
  for `0002` to `0009` from `django_migrations`, or start from an empty database.
- The document page's layout. The list of documents is now a card in a column of its own, titled
  "Documents", and the document's name sits over the wording, not across the whole page. On
  wide screens the card stays in view while the document scrolls. The page loads a new stylesheet,
  `mvp_compliance/pages.css`, which sets the card's offset below the top bar through the custom
  property `--mvp-compliance-header-clearance`. A project that replaces `document_detail.html`
  keeps its own layout. A project template that extends the package's and overrides `page.content`
  or `page.actions` must be updated, because the page no longer draws those blocks. The stylesheet
  is the first static file a public page of the package loads, so a deployment that uses a static
  files manifest runs `collectstatic` after upgrading. See [docs/pages.md](docs/pages.md).
- Requires django-mvp 0.25.0 or later (was 0.23.0). django-mvp 0.25.0 mounts its own URLs at the
  site root, so a project that includes `mvp.urls` does it with `path("", include("mvp.urls"))`.
- The slug `agreed` is no longer available to a document, because it is the address of the list of
  agreed documents. The admin and `full_clean()` refuse it, through `Document.RESERVED_SLUGS` and
  the validator `mvp_compliance.models.unreserved_slug`. See [docs/models.md](docs/models.md).

- A version is numbered when it is published instead of when its draft is created, and the number
  is the year of publication and its place among the document's versions published that year,
  such as `2026.2`. The count starts again each year, using the site's time zone. A draft has no
  number, so drafts that are never published leave no gaps. `Version.number` is now a string, or
  `None` for a draft, and versions are ordered by when they were published, with drafts last. The
  admin shows "Draft" where a draft's number would be.
- The package is built with hatchling instead of poetry-core, and developed with uv instead of
  Poetry. The wheel contains the same files as before. The source distribution does too, plus the
  repository's `.gitignore`, which hatchling includes so that a build from it leaves out the same
  files.
