# Pages

Each document that has a version in force is readable as a page of your site, in the
django-mvp shell, at an address that does not change when a new version is published.
Anyone can read it, signed in or not.

The package serves two more pages. One asks a signed-in person to agree to what is
outstanding for them, and is described under
[Asking a person to agree](#asking-a-person-to-agree). The other is in django-mvp's account
area: a signed-in person's own list of the documents they agreed to, described under
[What a person has agreed to](#what-a-person-has-agreed-to).

## Mounting the addresses

Include the package's URLs under a prefix of your choosing:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("legal/", include("mvp_compliance.urls")),
]
```

The pages render inside the shell, and the shell needs the menu renderers django-mvp
documents for its install. Without `FLEX_MENUS` in your settings, rendering any
django-mvp page raises. The package adds nothing to your own menus: which pages appear in
navigation is your decision. It adds one entry, described under [The menu](#the-menu), to
the account area's menu.

The list of what a person agreed to belongs to the account area, whose breadcrumb it links
to. Mount django-mvp's own URLs as well, as django-mvp documents:

```python
urlpatterns = [
    path("", include("mvp.urls")),
    path("legal/", include("mvp_compliance.urls")),
]
```

The list of what a person agreed to appears when a project mounts both: the package's URLs,
for the page, and django-mvp's, for the account area it belongs to. Leaving either out breaks
nothing and changes nothing else:

- **Without django-mvp's URLs**, the account area does not exist. The list's address answers
  "not found" for everyone, signed in or not, and an anonymous visitor is not sent to sign in
  for a page that is not there. The document pages keep working and hold no link to the list.
- **Without the package's URLs**, the account area has no entry for the list and nothing
  fails. Its other pages and its menu are as they were.

The package checks for the account area on each request, by looking for django-mvp's
`account-center` address, so there is no setting to change in either case.

## The address

| URL name | Arguments | Address | View |
|---|---|---|---|
| `mvp_compliance:agree` | none | `<prefix>/agree/` | `mvp_compliance.views.AgreementView` |
| `mvp_compliance:agreed` | none | `<prefix>/agreed/` | `mvp_compliance.views.AgreedDocumentsView` |
| `mvp_compliance:document` | `slug` | `<prefix>/<slug>/` | `mvp_compliance.views.DocumentView` |

The list's address is checked first, so no document is served at the slug `agreed`. The
admin and `full_clean()` refuse that slug; see [Documents](models.md#document). The
page that asks is checked ahead of the slug route too, so the slug `agree` never reaches a
document: give a document another slug.

There is one page per document: its address always shows the version in force. The same
address with `?version=<number>` shows that published version, current or superseded,
for as long as it stays published — a number such as `2026.1` or `2026.12`. A `?version=`
value that names no published version of the document is "not found".

The slug is the document's `slug` field, so `Document(slug="privacy-policy")` is served
at `legal/privacy-policy/` under the mount above. Link to it from a footer, or anywhere
else in a template:

```html
<a href="{% url 'mvp_compliance:document' 'privacy-policy' %}">Privacy policy</a>
```

An impressum is linked the same way, from the footer of the site, wherever the law of your
country expects to find it:

```html
<a href="{% url 'mvp_compliance:document' 'impressum' %}">Impressum</a>
```

## What a visitor sees

The page shows the document's name, a line under it, and the wording of the version
shown: the version in force by default, or the one named by `?version=`. When a new
version is published, the plain address shows it at once; an earlier `?version=` address
keeps showing what it always showed.

On wide screens the page is two columns. The left column is a card titled "Documents" that
lists every document with a version in force, alphabetically, each linking to its own page,
with the one being shown marked. The right column holds the document's name, the version
switcher and the wording. On a narrow screen the card stacks above the document. A document
with only drafts, or with no versions, is left out. The list is the same on a `?version=`
address as on the plain one.

The card stays in view while a long document scrolls. It stops below the shell's top bar,
at an offset the package's stylesheet, `mvp_compliance/pages.css`, sets to `5rem`. If your
project's top bar is a different height, set the custom property in your own stylesheet:

```css
:root {
  --mvp-compliance-header-clearance: 6rem;
}
```

The line under the name reads `v2026.1 - 26 September 2026`: the shown version's
number and the day it was published, in the project's date format. When the signed-in
visitor has accepted that version it continues `· Agreed on 27 September 2026`, with the
date of their acceptance. An anonymous visitor, and someone who has accepted a different
version of the document but not this one, see the first part only.

A notice, such as an impressum, is read and never accepted, so its line is the first part
only for everybody: no `Agreed on`, even for a signed-in visitor who accepted the document
before it became a notice, and on an earlier `?version=` address as on the plain one. The
rest of the page is the same as any document's, and the list beside the wording names it
along with the documents people agree to.

The page builds this line with `mvp_compliance.views.VersionSubtitleMixin`. A project
view that shows a version and wants the same line mixes it in ahead of the django-mvp
detail view and defines `get_version()`.

The wording is the `html` stored on the version when it was published, written out
as it is stored. Nothing renders Markdown while the page is served. That HTML is what the
configured renderer produced and sanitised at publication, so a project that points
`MVP_COMPLIANCE_RENDERER` at a renderer with a looser allow list serves that looseness on
its own pages.

## Asking a person to agree

`<prefix>/agree/` asks a signed-in person to agree to every document that is outstanding for
them: each document people agree to that has a version in force the person has not accepted.
A notice is never listed, and neither is a document with only drafts.

**What it lists.** One row for each outstanding document, in alphabetical order. A row holds the
document's name, the number of the version in force, a link that opens that exact version's page
(`?version=`) in a new tab, and a toggle. The page itself carries none of the wording: the link is
how it is read in full. A person who accepted an earlier version is asked about the version in
force. Every row is marked required.

**What a submission records.** One acceptance for each row whose toggle was on, written in one
go with [`Acceptance.objects.record_many()`](models.md#recording-several-at-once), and holding
the connecting address when `MVP_COMPLIANCE_RECORD_IP_ADDRESS` is on. Only the version in force
of a document outstanding for that person is recorded. Any other value in the submission, such
as a replaced version, a draft, a notice's version or text that names no version, is passed
over and records nothing. Opening the page records nothing, and neither does a submission with
no toggle on. Submitting the same agreement again records nothing new.

**Where the person goes.** After the write the page asks again what is outstanding, from the
stored acceptances and never from the submission. When nothing required is left, the person is
sent to the address in `next`, taken from the submitted form and otherwise from the query
string. The address is kept only when it is on the same site. An address on another host, with a
scheme other than `http` or `https`, with `http` when the request came over HTTPS, or
protocol-relative to another host, is replaced by `/`. When something required is left, as
after a submission with no toggle on, the page is drawn again with a message saying so.

**Agreeing to some of them.** A person may agree to part of the list. What was agreed to is
recorded and the page is drawn again with the rest, still in alphabetical order. Agreeing to
the last of them sends the person to the address they were first heading for.

**When the list changed while it was open.** A version published after the page was drawn
replaces the one the person was shown. Nothing is recorded for it, since they never saw its
wording. The versions still in force that were agreed to are recorded, and the page is drawn
again with the version now in force and a message saying a document changed, in place of the
one saying something required is left. A document accepted elsewhere, or made a notice,
since the page was drawn is passed over, and the rest are recorded as usual.

```html
<a href="{% url 'mvp_compliance:agree' %}?next=/dashboard/">Review our documents</a>
```

**When an acceptance cannot be stored.** The acceptances of one submission are written inside
one database transaction, so they are stored together or not at all. When the write fails with
a `DatabaseError`, or the package refuses a version with a `RecordError`, none of that
submission's acceptances is kept and every document is still outstanding for the person. They
are not sent on: the page is drawn again with a message saying their agreement was not
recorded, and the toggles that were on are still on, so submitting again is one click. The
message does not say why, and nothing about the cause reaches the page. Submitting again once
the write works records the acceptances and sends the person on to the address they were first
heading for.

**How the failure is reported.** The failure is logged at error level, with its traceback, on
the `mvp_compliance.views` logger, the module's `logger`. Under Django's default `LOGGING` that goes to standard
error and nowhere else. A project that mails or forwards its errors attaches its handler to
that logger, as it would for any of its own:

```python
# settings.py
LOGGING = {
    "version": 1,
    "handlers": {"mail_admins": {"class": "django.utils.log.AdminEmailHandler"}},
    "loggers": {
        "mvp_compliance.views": {"handlers": ["mail_admins"], "level": "ERROR"},
    },
}
```

**Who may use it.** A visitor who is not signed in is sent to `LOGIN_URL` with the page's full
address, `next` included, to come back to. A submission needs Django's CSRF token. The page
applies the protection itself, so a project without `CsrfViewMiddleware` refuses a forged
submission all the same.

**What it does not do.** It stops nobody. A person is free to leave the page, and leaving
records nothing. Nothing in the package links to the page or sends anyone there: when a person
is sent to it, and which documents hold them up, is a decision for the project.

## What a person has agreed to

A signed-in person finds their own list at `<prefix>/agreed/`, in django-mvp's account area.
It has one card for each document people agree to that the person has accepted at least one
version of. Documents are in alphabetical order by their present name, so a renamed document
appears under its new name. Each card holds a table with one row per version the person
accepted, newest published first: the version's number, linking to that version's page with
`?version=`, a badge saying whether it is in force or has been replaced, and the day the person
accepted it. The link works for a replaced version as for the one in force, and shows the
wording exactly as it was published.

Three things are left out. A document the person never accepted is not listed. A version the
person never accepted is not a row, even between two they did accept. A notice is not
listed, because nobody agrees to it. If a document is made a notice, its entry disappears;
change it back and the entry returns with the same acceptances, because nothing recorded is
touched. A person who has accepted nothing sees the page with a line saying so.

A document with more than four accepted versions shows the three newest in its table. The
rest sit under a line that counts them, which opens in place. With four or fewer, every
version is shown. Setting `shown_first` on a subclass of `AgreedDocumentsView` changes the
three.

When a document's version in force is one the person has not accepted, its card opens with a
statement of that: the version's number, the day it came into force, and that the person has not
agreed to it. A link beside it leads to the document's own page, which shows the version in
force. The statement is there only when none of the person's acceptances of the document is of
the version in force, so a person who accepted the version in force, with or without earlier
ones, sees none. The page is read each time it is opened, so a version published after the
person's last visit appears with nothing else done. The page has no button to accept the
version it points to and no form of any kind: reading the document is the only thing it offers.

The records are the reader's own and no one else's. The page needs a signed-in person and
sends anyone else to the project's sign-in page, so a visitor who is not signed in receives
none of the content. That page is whatever `LOGIN_URL` names. A project that mounts
django-mvp's account area sets `LOGIN_URL = "account_login"`, as django-mvp's own
documentation says, because Django's default address is one nothing registers. It reads only the signed-in account, never a value in the address, so
a staff member sees their own acceptances, not other people's. The records are found through
`Acceptance.objects.for_person()`, the same way as everywhere else in the package. The page
answers `GET` and `HEAD` only, and opening it writes nothing.

## The menu

The package adds nothing to your own menus, `AppMenu` and `MobileFooterMenu`: which pages
appear in navigation is your decision. It adds one entry, labelled "Agreements", to
django-mvp's account area menu, `AccountCenterMenu`. The entry leads to the list above and is
the selected one on it. If your project does not mount the package's URLs, the address does
not resolve and the menu leaves the entry out. If it does not mount django-mvp's URLs, there
is no account area menu to hold the entry; see [Mounting the addresses](#mounting-the-addresses).

A host project adds its own entry, as the demo does in `demo/menus.py`, here
pointing at one document's page:

```python
from django.urls import reverse_lazy
from flex_menu import MenuItem
from mvp.menus import AppMenu

AppMenu.append(
    MenuItem(
        name="legal-documents",
        url=reverse_lazy("mvp_compliance:document", args=["privacy-policy"]),
        extra_context={"label": "Legal documents", "icon": "file-earmark-text"},
    )
)
```

A document page's breadcrumbs are the document's name alone. A `?version=` address shows the
same trail as the plain one. The list's trail is the account area, then the list.

## The version switcher

Every document page carries a version switcher among its actions: a primary button,
labelled with the version shown and a dropdown caret, listing every published version of
the document, newest first, each as `v2026.1 - 26 September 2026` linking to the same
page with `?version=` and that number. The version shown is marked. The switcher is there
even when the document has only one published version, and drafts are never listed.

## A superseded version

When `?version=` shows a version that is no longer in force, the page carries one alert
row above the wording: a notice that the version was replaced, the date it came into
force and the date it was replaced, and a "View current version" button leading to the
document's plain address, which always shows the version now in force. The version in
force shows no such alert, whether it is reached with no parameter or with its own number
as `?version=`.

## When the page is "not found"

The page answers 404, to every visitor whether signed in, staff or anonymous, when:

- no document has that slug,
- the document has no version in force, because it has no versions or only drafts, or
- `?version=` names a value that is not a published version of the document — a draft's
  number (a draft has none), another document's number, or anything else.

Nothing on the page links to editing or deleting a document. That is done in the admin.

## Overriding a template

Every page has one template under `mvp_compliance/`. The document page extends django-mvp's
`page_view.html` and fills its `styles` and `page.content-wrapper` blocks. It replaces the
wrapper whole, so the `page.title`, `page.actions` and `page.content` blocks inside it are not
drawn on this page, and a project template that extends the package's and overrides one of
them has no effect. The list extends `mvp/account/base.html` and fills its `account.content`
block, and draws its rows through the partial `mvp_compliance/_agreed_version_rows.html`. To
restyle a page, place a template at the same path in your project. Django finds yours first,
and the package's is never used for that page. The package needs no other
change, and you do not fork it.

| Template path | Page | Receives |
|---|---|---|
| `mvp_compliance/document_detail.html` | `mvp_compliance:document` | `document`, `version`, the version shown, carrying `replaced_at`: the date the next version was published, or `None` for the version in force, and `versions`, every published version of the document newest first, and `documents`, every document that has a version in force in name order |
| `mvp_compliance/agreement.html` | `mvp_compliance:agree` | `entries`, one per outstanding document, each with `document`, `version`, `optional` and `field`, the attributes of its toggle; `required_count`, `destination`, `redirect_field_name`, `missing` after a submission that leaves something required, and `changed` after one made from a list in which a version was replaced or a document published |
| `mvp_compliance/agreed_documents.html` | `mvp_compliance:agreed` | `entries`, one per document in name order. Each has `document`, `shown`, the person's acceptances drawn in the table, `earlier`, the acceptances folded under the count, and `newer`, the version in force when the person has not accepted it, otherwise `None`. Each acceptance carries its `version` and `accepted_at` |

Every page also receives django-mvp's `page` context: its title and breadcrumbs.

A project's own `mvp_compliance/document_detail.html`, for example:

```html
{% extends "page_view.html" %}
{% block page.content %}
  <article class="prose max-w-none">{{ version.html|safe }}</article>
{% endblock page.content %}
```

`version.html` is the sanitised HTML stored at publication, so write it out with `|safe`
and render nothing else from Markdown. Put your template's directory in
`TEMPLATES["DIRS"]`, or in an app listed before `mvp_compliance` in `INSTALLED_APPS`.
Strings you add are yours to translate.
