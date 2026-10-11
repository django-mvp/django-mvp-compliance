# Sketch: asking a signed-in person to agree to what is outstanding

A prototype of the page, built to be looked at before the implementation is planned. It has no
tests. The templates, the markup and the wording are what is being reviewed. The code behind them
is a stand-in that the plan may keep, change or rebuild.

## What exists

**The records the page reads and writes**

- `Document.objects.outstanding_for(user)` gives the documents whose version in force the person
  has not accepted, notices left out, in one query. Chained with `in_force()` each document carries
  its current version, so the page costs no query per document.
- A version holds its number, the date it was published and the HTML stored at publication. The
  page serves that HTML and renders nothing.
- `Acceptance.objects.record(user, version, request=...)` writes one acceptance and returns the
  existing one when the same person accepts the same version twice. It raises `RecordError` for a
  notice or a draft.
- `Acceptance.objects.for_person(user)` finds a person's earlier acceptances, which is how the page
  can say which version of a document they last agreed to.
- Nothing stored says where a person was heading. The destination arrives with the request.

**What is already there to build with**

- django-mvp's `MVPTemplateView` and `page_view.html` give the page its title, subtitle and trail
  inside the shell. `page_view.html` has a `page.header` block that sits above the title.
- `c-card`, `c-alert`, `c-button`, `c-form` and `c-form.field` cover the page. `c-form.field` draws
  a checkbox with its label wrapped around it and no fieldset.
- The document page already serves a version's stored HTML inside `prose`.
- django-mvp's sign-in page sends a person back to the address they were stopped at, with its
  query string.

**Components that fit, and what does not quite**

- The label of a `c-form.field` checkbox does not wrap by default. A long document name needs the
  label text passed through the slot with a wrapping utility on it.
- The shell's stylesheet ships no maximum-height utility of a useful size, so the region that holds
  a document's wording gets its height from a rule in the package's own stylesheet.
- Django's messages are drawn by the shell as toasts in a corner. They are not used here: a
  message about a failed record has to stay on the page, above the title.

## What the screens need from the code

- Every document outstanding for the signed-in person, with its version in force, in the order the
  document pages list documents in.
- For each of those documents, the person's most recent acceptance of an earlier version, when
  there is one, with its number and date.
- The stored HTML of each version in force.
- The address to return to, kept through signing in and through every time the page is shown again.
- After a submission: which documents were recorded, whether the write failed, whether nothing was
  ticked, and which documents were replaced by a newer version while the person was reading.
- The boxes a person ticked, kept ticked when the page comes back after a failed write.
- Whether the page shows one document or several, because the layout differs.
- A redirect, with no page drawn, for a person with nothing outstanding.
- A count of database queries that does not grow with the number of documents outstanding.
- An address for the page that sits beside the document pages and cannot be taken by a slug.

## What the sketch faked

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
- **A version replaced while the person was reading.** The message for it is in the template and
  the view works out when to show it, but the demo has no way to publish a version in the middle
  of a visit, so it has not been seen on a running page.
- **The address.** The page answers at `agree/` and the slug `agree` is now refused for a document,
  beside `agreed`. No migration or test covers it.
- **Translations.** The new strings are marked for translation. No catalogue was updated.
- **Documentation.** None written.
- **A project that replaces the template.** Not tried.
- **Demo accounts.** Two accounts were added so every state is reachable, and the landing page
  lists which account shows which state. An acceptance cannot be undone, so an account that agrees
  in the demo stays agreed until the demo database is rebuilt.

## What was ruled by eye

These are choices with no settled answer. Each is open to change in review.

- One column, no wider than comfortable reading width, with one card per document.
- A page with one document shows its wording at full length. A page with several holds each
  wording in a region about twenty lines tall that scrolls, so the box beneath it stays in reach.
  The height is a custom property a project can override.
- The box that agrees to a document sits directly under that document's wording, inside its card.
  Its label names the document and the version.
- Under each document's name, one line gives the version, the date it came into force, and the
  version the person last agreed to when there is one. A link opens the document on its own page
  in a new tab.
- One button at the foot of the page, labelled "Agree and continue". With several documents, a
  line beside it says some can be agreed to now and the rest later.
- The page has no button for declining or leaving. A person leaves by the site's own navigation.
- Messages sit above the page title: an error when the record was not written, an error when
  nothing was ticked with a button to the first box, a confirmation for each document recorded
  when others remain, and a note when a document was replaced during the visit.
- After a failed write the boxes stay ticked. After a partial agreement the remaining boxes are
  empty.
- The page is titled "Documents to agree to", with the same title for one document as for several.
- Dates are shown without the time of day.
