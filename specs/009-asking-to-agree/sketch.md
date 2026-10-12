# Sketch: asking a signed-in person to agree to what is outstanding

A prototype of the page, built to be looked at before the implementation is planned. It has no
tests. The templates, the markup and the wording are what is being reviewed. The code behind them
is a stand-in that the plan may keep, change or rebuild.

## What exists

**The records the page reads and writes**

- `Document.objects.outstanding_for(user)` gives the documents whose version in force the person
  has not accepted, notices left out, in one query. Chained with `in_force()` each document carries
  its current version, so the page costs no query per document.
- A version holds its number and has a page of its own at the document's address with
  `?version=<number>`. That page serves the wording stored at publication.
- `Acceptance.objects.record(user, version, request=...)` writes one acceptance and returns the
  existing one when the same person accepts the same version twice. It raises `RecordError` for a
  notice or a draft.
- Nothing stored says where a person was heading. The destination arrives with the request.

**What is already there to build with**

- django-mvp's `MVPTemplateView` and `page_view.html` give the page its title, subtitle and trail
  inside the shell. `page_view.html` has a `page.header` block that sits above the title.
- `c-card`, `c-alert`, `c-button`, `c-form` and `c-form.field` cover the page. `c-form.field` draws
  a toggle with its label wrapped around it and no fieldset. The list itself is DaisyUI's `list`
  and `list-row`, which the shell's stylesheet ships.
- django-mvp's sign-in page sends a person back to the address they were stopped at, with its
  query string.

**What does not quite fit**

- Django's messages are drawn by the shell as toasts in a corner. They are not used here: a
  message about a failed record has to stay on the page, above the title.

## What the screens need from the code

- Every document outstanding for the signed-in person, with its version in force.
- For each document, whether the person may continue without agreeing to it. Required documents
  come first, optional ones after, and each kind keeps the order the document pages use.
- The address of the page that serves each listed version.
- The address to return to, kept through signing in and through every time the page is shown again.
- The person sent on once nothing required is outstanding, whether or not they agreed to an
  optional document. A page with only optional documents is still shown when it is opened.
- After a submission that does not send them on: whether the write failed, whether a required
  document was left without agreement, and whether a listed version was replaced meanwhile.
- The toggles a person switched on, kept on when the page comes back after a failed write.
- A refusal, on the server, of a submission that leaves a required document without agreement. The
  disabled button is a convenience for a browser running the script.
- A redirect, with no page drawn, for a person with nothing outstanding.
- A count of database queries that does not grow with the number of documents outstanding.
- An address for the page that sits beside the document pages and cannot be taken by a slug.

## What the sketch faked

- **Required and optional documents.** Whether a document stops a person is a later feature (#87)
  and nothing in the package stores it. The demo names the optional documents in a setting,
  `MVP_COMPLIANCE_SKETCH_OPTIONAL_SLUGS`, which the view reads. No model field was added. The
  setting, the ordering and the rule for when a person is sent on are stand-ins for what that
  feature will supply.
- **A submission that leaves a required document without agreement.** The view records whatever
  was agreed to, as the specification says, and shows the page again with the alert. Only a
  browser without the script can send such a submission.
- **The view and its queries.** Written directly to make the page real, with no tests and no check
  on the number of queries. The acceptances of one submission are written inside one transaction,
  and the page asks again what is outstanding before sending anybody on, but neither is proven.
- **The failed write.** The demo refuses to store an acceptance for one account,
  `unrecorded.user@example.com`, through a signal receiver in `demo/signals.py`. The package has no
  such switch and gets none. The view catches a database error and a refused record. Whether those
  are the right errors to catch, and how the failure reaches the project's error reporting, is
  undecided: the sketch writes it to the log.
- **The default destination.** A person with no usable destination is sent to the site's root. The
  view reads a setting, `MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL`, that is documented nowhere and
  whose name is a placeholder.
- **The destination check.** An address on another site and the page's own address are replaced by
  the default. Other loops, such as a destination that itself sends the person back, are not
  considered.
- **A version replaced while the person was on the page.** The message for it is in the template
  and the view works out when to show it, but the demo has no way to publish a version in the
  middle of a visit, so it has not been seen on a running page.
- **The button's script.** A few lines in `agreement.js`, written without tests and not run in a
  browser by the author.
- **The address.** The page answers at `agree/` and the slug `agree` is now refused for a document,
  beside `agreed`. No migration or test covers it.
- **Translations.** The new strings are marked for translation. No catalogue was updated.
- **Documentation.** None written.
- **A project that replaces the template.** Not tried.
- **Demo accounts.** Four accounts were added so every state is reachable, and the landing page
  lists which account shows which state. An acceptance cannot be undone, so an account that agrees
  in the demo stays agreed until the demo database is rebuilt.

## What was ruled by eye

Ruled in review of the prototype. The build may not undo these.

- The page does not show any document in full. Each document is one row of a list.
- A row holds the document's name, whether it is required or optional, its version, a link to
  that version's page, and a toggle.
- The agreement is a toggle, not a checkbox.
- Strings are short and fixed, with no document name or version number worked into a sentence.
  The toggle's label is "I agree". The link reads "View document in full". The document's name
  reaches assistive technology through the row, not through a longer label.
- The two kinds are called "required" and "optional" everywhere on the page.
- "Required" and "Optional" are badges: the primary variant for required, the neutral variant for
  optional. The version stays as plain text beside the badge.
- The toggle and its label sit at the end of every row, so the toggles form one column down the
  list. A long document name wraps in its own column and never moves the toggle, at any width.
- When a required document is on the page, the line under the title reads "You will not be able
  to use the app without agreeing to all required documents." Nothing about optional documents
  sits beside the button.
- When a required document is left without agreement, the alert reads "All documents marked as
  required need your agreement." It has no button.
- The submit button is disabled until every required document's toggle is on. With nothing
  required on the page it is enabled from the start.

Choices made in building it, each open to change:

- One column at reading width, with the list inside a single card.
- Required documents come first, optional ones after.
- The link opens the version's page in a new tab, so the toggles already switched on are kept.
- One button at the foot of the list: "Agree and continue", or "Continue" when nothing on the page
  is required. With only optional documents the line under the title reads "Agreeing is optional."
- The page has no button for declining or leaving. A person leaves by the site's own navigation.
- Messages sit above the page title.
- After a failed write the toggles stay on.
- The page is titled "Documents to agree to", with the same title for one document as for several.
- A row does not say which version the person last agreed to.
