# Sketch — FS-013

## What exists

- The account area is django-mvp's: `mvp/account/base.html` puts a page beside
  `AccountCenterMenu`, to which `mvp_compliance/menus.py` already appends **Agreements** and
  **Your data**. The new page sits after them.
- `PersonalDataView` (`/legal/data/`) is the nearest page: it lists each declared kind's `heading`
  and `description` without gathering anything, is guarded by django-allauth's
  `reauthentication_required` on GET and POST, answers "not found" without an account area or
  allauth, and is mounted only while `MVP_COMPLIANCE_PERSONAL_DATA` is set. Its failure alert sits
  above the title.
- `PersonalData` has `heading`, `description`, `model`, `fields`, `get_queryset(user)` and
  `collect(user)`. It has nothing yet that says how a kind is deleted.
- `acceptances_survive_account_removal()` says whether a person's acceptances outlive the account.
  Under the default they do, and an acceptance keeps naming its version and when.
- Forms in the package's pages are drawn with `c-mvp.form`, which renders a Django form and its
  errors. Buttons are `c-button`, alerts `c-alert`, both from daisy-cotton.
- The demo declares two kinds, **Your profile** and **Files you uploaded**, and has allauth, so the
  identity check is allauth's own page.
- Planning note N1 (an `erase(user)` method on the same class) bears on nothing on screen.

## Design rationale

Written before the build. Class: **convention** (a source settles it) or **taste** (a choice).

1. Identity is confirmed before the page is shown, on allauth's own page, exactly as for **Your
   data**. **Convention**: the project's own pattern, ruled by Sam for FS-012.
2. The page is one screen: what will be deleted, what is kept, the link to a copy, then the
   confirmation. **Taste**: the identity check is already a step of its own, so a further "are you
   sure?" page would make three.
3. The list of what will be deleted is one row per declared kind, heading and one line, the same
   rows as **Your data**. **Convention**: the project's own pattern, and FR-002 asks for the same
   list in the same order.
4. A second card says what is kept: the record of the documents the person agreed to. Shown only
   when the project keeps them. Where the project removes them with the account, they join the list
   of what will be deleted instead. **Convention**: GOV.UK's warning-button guidance, the context must
   make clear what will happen, and ADR 0008 says the cost of keeping them is stated, never hidden.
5. The link to a copy comes before the confirmation, as an info alert inside the deletion card's
   flow rather than loose text between cards. **Convention**: FR-004, and the project's rule of no
   loose text between cards.
6. The person ticks a box saying they understand the deletion is permanent before the button does
   anything. Leaving it unticked shows the form's own error on the box. **Convention**: GOV.UK, an
   action with serious consequences gets an extra confirmation, and the field's error is shown at
   the field (WCAG 3.3.1).
7. The final button is the error colour and says **Delete my account**. **Convention**: GOV.UK
   warning buttons are for "permanently deleting an account", and the text must say what happens
   rather than rely on the colour.
8. A **Cancel** link beside the button returns to the account area. **Convention**: GOV.UK button
   groups pair the action with a way out.
9. The failure message sits above the title. **Convention**: the project's rule, alerts go above
   the title.
10. The page shown afterwards is an ordinary page in the shell, not in the account area, with one
    sentence and a link to the home page. **Convention**: nobody is signed in by then, and the
    account area needs a signed-in person.
11. The menu entry is **Delete account**, with the trash icon, last in the account area's menu.
    **Taste**: the destructive entry goes after everything a person might want first.

## What the screens need from the code

- The page needs every declared kind's heading and description, without gathering any records.
- The page needs to know whether the project keeps a person's acceptances when an account goes.
- The page needs to know whether the copy page exists, to link to it.
- The page and its menu entry need to know whether every declared kind says how it is deleted.
- The form needs the account's email address, or its username where it has none, to show in the
  label and to compare what is typed against, ignoring case and surrounding spaces.
- The page afterwards needs nobody signed in, and is reachable without an account.

## What the sketch faked

- No kind says how it is deleted. The page shows whenever kinds are declared, as **Your data**
  does.
- Submitting the confirmed form deletes nothing and signs nobody out. It goes straight to the page
  shown afterwards.
- `?state=failed` on the page shows the failure alert. In the build it comes from a kind's deletion
  failing.
- `?state=removed` on the page shows it as it reads when the project removes acceptances with the
  account: no "what is kept" card, and the agreements listed among what will be deleted. In the
  build it comes from the setting.
- The project is told nothing when an account is deleted (US-3).

## What was ruled by eye

- **Type to confirm, not a checkbox** (Sam, 2026-10-23). The person types their own email address
  before **Delete my account** does anything. Anything else shows the field's own error. The email
  address was chosen over a fixed word such as DELETE because it needs no translation and names
  the account being deleted. An account with no email address types its username. This replaces
  rationale item 6.
- Confirming identity on allauth's own page first is approved (Sam, 2026-10-23).
