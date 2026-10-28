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
| `mvp_compliance:comparison` | `slug` | `<prefix>/<slug>/compare/?from=<number>&to=<number>` | `mvp_compliance.views.ComparisonView` |
| `mvp_compliance:document` | `slug` | `<prefix>/<slug>/` | `mvp_compliance.views.DocumentView` |

The addresses of the list, of the page that asks, of the page a person downloads their data from,
and of the pages for deleting an account and after it are checked ahead of the slug route, so no
document is served at the slugs `agreed`, `agree`, `data`, `delete` and `deleted`. The admin and
`full_clean()` refuse all five; see [Documents](models.md#document). A document published under
one of them before it was reserved is not reachable at its page any more, and the address shows
the package's own page instead.
Creating a document under either slug through the ORM is not stopped, as for any slug rule.

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

A document declared in `MVP_COMPLIANCE_DOCUMENTS` (see [Declaring
documents](models.md#declaring-documents)) can be linked before anything is published. Its
address answers "not found" until a version is in force, then shows it.

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

The list of documents is django-mvp's side panel, titled "Documents". From the `lg` breakpoint
the page is two columns: the panel on the left lists every document with a version in force,
alphabetically, each linking to its own page, with the one being shown marked, and the right
column holds the document's name, the version switcher and the wording. The panel sticks under
the shell's header while a long document scrolls, at the header's measured height, so it needs
no offset from you. Below `lg` the panel is a drawer, opened by a "Documents" button next to the
version switcher. A document with only drafts, or with no versions, is left out. The list is the
same on a `?version=` address as on the plain one.

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

The page builds this line with `mvp_compliance.views.VersionLeadMixin`. A project
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
force, and the row also shows the [summary](authoring.md#saying-what-changed) of every version
published since the one they last accepted, newest first, each under its number. A version
published without a summary is left out of that list. A person agreeing to a document for the
first time sees no summaries.

A person who accepted an earlier version also gets a "See what's changed" link under the row. It
opens the [comparison](#comparing-two-versions) of the newest version they accepted with the
version they are asked about, in a new tab, so the form and the address they are heading for
stay as they were. A summary covers one step, and the comparison covers every step between the
two. A document the person never accepted has no such link, and opening the comparison records
nothing. A row is marked required when its document is [enforced](models.md#enforcement) and
optional when it is not, and the required rows come first.

**What a submission records.** One acceptance for each row whose toggle was on, written in one
go with [`Acceptance.objects.record_many()`](models.md#recording-several-at-once), and holding
the connecting address when `MVP_COMPLIANCE_RECORD_IP_ADDRESS` is on. Only the version in force
of a document outstanding for that person is recorded. Any other value in the submission, such
as a replaced version, a draft, a notice's version or text that names no version, is passed
over and records nothing. Opening the page records nothing, and neither does a submission with
no toggle on. Submitting the same agreement again records nothing new.

**Where the person goes.** After the write the page asks again what is outstanding, from the
stored acceptances and never from the submission. When no enforced document is left, the person
is sent on to the destination described under
[Sending a person to the page](#sending-a-person-to-the-page). When something required is left,
as after a submission with no toggle on, the page is drawn again with a message saying so.
See [ADR 0021](https://github.com/django-mvp/django-mvp-compliance/blob/main/docs/adr/0021-a-person-is-let-through-on-the-stored-acceptances-never-on-the-submission.md)
for why the page asks twice.

**Agreeing to some of them.** A person may agree to part of the list. What was agreed to is
recorded and the page is drawn again with the rest, required rows first. Agreeing to the last
enforced one sends the person to the address they were first heading for, whether or not they
agreed to the documents that are not enforced.

**Documents that are not enforced.** A document whose `enforced` is off, such as a cookie
policy, is listed on the page like any other, and agreeing to it records an acceptance like any
other. It is never needed to be sent on. A person who agrees to it and leaves an enforced
document alone is shown the page again, because the enforced one is still outstanding. A person
who leaves it alone and agrees to everything that is enforced is sent on, and it stays
outstanding for them.

A person with only documents that are not enforced outstanding is treated as follows:

| They open the page | The page |
|---|---|
| with a `next` parameter, whatever its value | Redirects at once, to `next` when it is an address the page follows and to the default destination when it is not. Nothing is drawn. |
| with no `next` parameter | Is shown, offering those documents. Whatever they agree to, including nothing, they are then sent to the default destination. |

An address to return to means the person was on their way somewhere, and is not held up over a
document they may leave. No address means they opened the page on purpose. A person with nothing
outstanding at all is sent on in both cases. The same rule holds whether or not the project has
listed the [middleware](enforcement.md), which only ever sends a person to the page while an
enforced document is outstanding for them.

**When the list changed while it was open.** A version published after the page was drawn
replaces the one the person was shown. Nothing is recorded for it, since they never saw its
wording. The versions still in force that were agreed to are recorded, and the page is drawn
again with the version now in force and a message saying a document changed, in place of the
one saying something required is left. A document accepted elsewhere, or made a notice,
since the page was drawn is passed over, and the rest are recorded as usual.

A change that lands in the instant between the page reading what is outstanding and writing the
acceptances is not caught this way. An acceptance of the version just replaced can be stored, or
the submission can be drawn as one that could not be recorded. The person is asked again in both
cases, because whether they are sent on is read after the write.

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

**What it does not do.** The page itself stops nobody. A person is free to leave it, and leaving
records nothing. Nothing in the package links to it. A person is sent to it from any address on
the site only when the project lists the middleware described in
[Enforcement](enforcement.md); without it, when a person is sent to it, and which documents hold
them up, is a decision for the project.

## Sending a person to the page

Nothing sends a person to the page until a project does. Send them to
`{% url 'mvp_compliance:agree' %}` from a link:

```html
<a href="{% url 'mvp_compliance:agree' %}">Review our documents</a>
```

A link with no `next` opens the page for a person who chose to open it, and shows them every
document outstanding for them, enforced or not. Add the address to come back to in `next` when
the person is on their way somewhere and has to agree first. They are then sent on at once when
nothing enforced is outstanding for them, as described under
[Asking a person to agree](#asking-a-person-to-agree).

From a view of your own, send a person on only when something enforced is outstanding for them,
so that a person who has agreed is not sent round again:

```python
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from mvp_compliance.models import Document


@login_required
def checkout(request):
    if Document.objects.enforced_outstanding_for(request.user).exists():
        query = urlencode({"next": request.get_full_path()})
        return redirect(f"{reverse('mvp_compliance:agree')}?{query}")
    ...
```

**How the destination is given.** In the `next` parameter of the query string, or in the
submitted form's `next` field when there is one. The page draws that address into its form on
every response, so it is still there when the page is shown again after a failed write or after
the person agreed to part of the list, and the person finally lands on the address they were
first given.

**Which addresses are followed.** Only an address on the same site. These are replaced by the
default destination below, and nothing is followed from them:

- an address on another host, a protocol-relative one, or one with a scheme other than `http`
  or `https`;
- an address with `http` when the request came over HTTPS;
- the page's own address, so that a person is never sent round the page again. That is the
  page with a query string, without its trailing slash, with a letter percent-encoded, and `.`
  or a bare `?x=1`, which a browser resolves to the page;
- no address at all.

**The default destination.** `MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL` names where a person
goes when no usable destination was given. It is a path or the name of a URL, and `/` when the
project sets none:

```python
# settings.py
MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL = "/"  # the default
MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL = "/welcome/"  # a path
MVP_COMPLIANCE_AGREEMENT_REDIRECT_URL = "dashboard"  # the name of a URL
```

The value goes through Django's `resolve_url()`, so a name is reversed on every use. The setting
is yours and is not checked against the site: it is followed as written.

**A person with nothing outstanding.** Opening the page answers with a redirect to the
destination, or the default, and draws nothing, with or without a `next`. Nothing is recorded
and the person is shown no page. A person who agreed somewhere else between the project's own
check and the page is sent on in the same way. A person with only documents that are not
enforced outstanding is sent on in the same way when the request carries a `next`.

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
agreed to it. Two links sit beside it. One leads to the document's own page, which shows the
version in force. The other, "See what's changed", opens the [comparison](#comparing-two-versions)
of the newest version the person accepted with the version in force. The statement is there only when none of the person's acceptances of the document is of
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

A host project adds its own entry, here pointing at one document's page:

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
force and the date it was replaced, a "See what's changed" button leading to the
[comparison](#comparing-two-versions) of that version with the version in force, and a
"View current version" button leading to the document's plain address, which always shows
the version now in force. The version in
force shows no such alert, whether it is reached with no parameter or with its own number
as `?version=`.

## Comparing two versions

The comparison page shows the wording of two published versions of one document as a single
text: words the newer version added are marked as added, and words it removed are marked as
removed. Everything else reads as it does on the document's page. Above the text, both
versions are named with the dates they were in force and a link to each one's page, and two
dropdowns choose the older and the newer version. When the two read the same, a notice says so
and the text is shown unmarked.

Anyone can read it, signed in or not. The address names the two versions by number, in either
order:

```python
from django.urls import reverse

address = reverse("mvp_compliance:comparison", args=["privacy-policy"])
# "/legal/privacy-policy/compare/" - add the two numbers as the query string
link = f"{address}?from=2026.1&to=2026.3"
```

`from` and `to` are the numbers of two published versions of the document. The older is always
shown first, so `?from=2026.3&to=2026.1` shows the same page. The marks are worked out from the
text each version stored when it was published, so a published address keeps showing the same
comparison after a newer version is published.

The document's page offers it. When a document has more than one published version, a
"See what's changed" dropdown beside the version switcher lists every other published version,
each linking to its comparison with the version shown. A replaced version's notice links to the
comparison with the version in force. To link to a comparison from your own templates:

```html
<a href="{% url 'mvp_compliance:comparison' 'privacy-policy' %}?from=2026.1&amp;to=2026.3">What changed</a>
```

In an email, where the link must carry the site's address, build it in code with `reverse`
as above and put the site's address in front of it:

```python
link = f"https://example.com{address}?from=2026.1&to=2026.3"
```

The page answers 404, to every visitor, when the slug names no document in force, the document
has only one published version, `from` or `to` is missing, or either names anything but a
published version of this document: a draft (it has no number), another document's number, or
an unknown one. The page is `mvp_compliance/comparison.html`; place a template at that path to
replace it. It is given `comparison`, `versions` and `document`.

`comparison` is a `mvp_compliance.comparison.Comparison`, which you can also build yourself from
two published versions of one document, given in either order:

```python
from mvp_compliance.comparison import Comparison

comparison = Comparison.of(first, second)
comparison.older, comparison.newer  # ordered by when each was published
comparison.same  # True when the two read the same, tags and spacing aside
comparison.html()  # the newer text, with <ins> and <del> around the differences
```

`html()` is safe to place in a template as it is. Each mark starts with a hidden label, so a
screen reader announces what was added or removed.

Changes are marked word by word within a paragraph, a heading or a list item. One that holds more
than 2,000 words (`Comparison.longest`) is marked as removed and added whole, which keeps a
comparison quick. A removed table cell's words are shown beside the table rather than in it.

## When the page is "not found"

The page answers 404, to every visitor whether signed in, staff or anonymous, when:

- no document has that slug,
- the document has no version in force, because it has no versions or only drafts, or
- `?version=` names a value that is not a published version of the document — a draft's
  number (a draft has none), another document's number, or anything else.

Nothing on the page links to editing or deleting a document. That is done in the admin.

## Overriding a template

Every page has one template under `mvp_compliance/`. The document page extends django-mvp's
`page_view.html` and fills its `page.side`, `page.actions` and `page.content` blocks: the list of
documents, the version switcher with the button that opens the list on a narrow screen, and the
wording. The title comes from the page's own `page.title` block. A project template that extends
the package's can override any one of those blocks and keep the rest. The list extends
`mvp/account/base.html` and fills its `account.content` block, and draws its rows through the
partial `mvp_compliance/_agreed_version_rows.html`. To restyle a page, place a template at the same
path in your project. Django finds yours first, and the package's is never used for that page. The
package needs no other change, and you do not fork it.

| Template path | Page | Receives |
|---|---|---|
| `mvp_compliance/document_detail.html` | `mvp_compliance:document` | `document`, `version`, the version shown, carrying `replaced_at`: the date the next version was published, or `None` for the version in force, and `versions`, every published version of the document newest first, and `documents`, every document that has a version in force in name order |
| `mvp_compliance/agreement.html` | `mvp_compliance:agree` | `entries`, one per outstanding document, required first, each with `document`, `version`, `optional`, `field`, the attributes of its toggle, `changes`, the summaries of what changed, and `since`, the newest version the person accepted, for the link to the comparison, or `None`; `required_count`, the number of entries that are not optional; `destination`, the address to go on to; `redirect_field_name`, the name to send it under; `failed` after a submission whose acceptances could not be stored; `missing` after one that leaves something required; and `changed` after one made from a list in which a version was replaced or a document published |
| `mvp_compliance/agreed_documents.html` | `mvp_compliance:agreed` | `entries`, one per document in name order. Each has `document`, `shown`, the person's acceptances drawn in the table, `earlier`, the acceptances folded under the count, `newer`, the version in force when the person has not accepted it, otherwise `None`, and `since`, the newest version they accepted, for the link to the comparison whenever `newer` is set. Each acceptance carries its `version` and `accepted_at` |
| `mvp_compliance/comparison.html` | `mvp_compliance:comparison` | `comparison`, a `Comparison` of the two versions named by `from` and `to`, with `older` and `newer`; `versions`, every published version of the document newest first; `document`; and `documents`, every document that has a version in force in name order |

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

### Replacing the page that asks

Place a template at `mvp_compliance/agreement.html` and the page uses it in place of the
package's, which extends `page_view.html` and fills `page.header`, `page.content-wrapper` and
`extra_js`. The page still records and sends the person on as before: that is done by the view,
and the template only has to send it what it reads. The form must send:

- `agree`, once for each toggle that is on, with the version's id: `entry.field.value`;
- `listed`, once for each entry the page showed, on or off, with `entry.version.pk`. It decides
  which message is drawn when something required is left, so a submission without it is always
  drawn as `changed`;
- `redirect_field_name`, as a field of that name carrying `destination`;
- the CSRF token.

```html
{% extends "page_view.html" %}
{% block page.content %}
  {% if failed or missing or changed %}<p role="alert">...</p>{% endif %}
  <form method="post" id="agreement">
    {% csrf_token %}
    <input type="hidden" name="{{ redirect_field_name }}" value="{{ destination }}">
    {% for entry in entries %}
      <input type="hidden" name="listed" value="{{ entry.version.pk }}">
      <label>
        <input type="checkbox" name="{{ entry.field.name }}"
               value="{{ entry.field.value }}"
               {% if entry.field.checked %}checked{% endif %}>
        {{ entry.document.name }}{% if not entry.optional %} *{% endif %}
      </label>
    {% endfor %}
    <button type="submit">{% if required_count %}Agree and continue{% else %}Continue{% endif %}</button>
  </form>
{% endblock page.content %}
```

`entry.field` holds the toggle's attributes: `name`, `value`, `id`, `aria-describedby`,
`data-required` on a required entry and `checked` when the toggle was on in a submission that
failed. Hyphenated keys cannot be read in a template, so to draw all of them pass the whole
`entry.field` to a component's `attrs`, as the package's own row does:
`<c-compliance.outstanding :document="entry.document" :version="entry.version" :field="entry.field" :optional="entry.optional" />`
draws one row, hidden `listed` field included, for use inside a `<ul class="list">`.

The package's script, `mvp_compliance/agreement.js`, keeps the submit button disabled until
every `data-required` toggle is on. It finds the form by the id `agreement`, the toggles by
`data-required` and the button by `type="submit"`. Load it with
`{% static 'mvp_compliance/agreement.js' %}` and keep those three, or leave it out: the server
refuses a submission that leaves something required whatever the page does.

### Deciding which documents are required

`AgreementView.is_optional(document)` answers for each outstanding document whether the person may
go on without it, and the package's view reads the document's `enforced` field: a document is
optional when it is not enforced. A project's own view may override it to make a document that
is not enforced required on the page, by calling `super()` and adding to the answer:

```python
# views.py
from mvp_compliance.views import AgreementView


class ProjectAgreementView(AgreementView):
    def is_optional(self, document):
        return super().is_optional(document) and document.slug != "cookie-policy"
```

An override must not make an enforced document optional on a site that has listed the
[middleware](enforcement.md). The middleware asks
`Document.objects.enforced_outstanding_for(user)` and never the view, so a person who left an
enforced document alone would be sent back to the page by the middleware and sent on by the
page, round and round. To let a document go, switch its `enforced` off. Routing the view is
described under [Changing how an agreement is stored](#changing-how-an-agreement-is-stored).

### Changing how an agreement is stored

`AgreementView.record_agreed(versions)` is the one place the page writes, and the one method a
project's own view overrides to change how an agreement is stored. It is called once for a
submission that agreed to something, inside a database transaction, with the versions in force
of the documents that were outstanding for the person. Call `super()` to keep the package's
acceptances and add your own bookkeeping beside them:

```python
# views.py
from mvp_compliance.views import AgreementView


class ProjectAgreementView(AgreementView):
    def record_agreed(self, versions):
        super().record_agreed(versions)
        AuditEntry.objects.create(user=self.request.user, versions=len(versions))
```

Mount it ahead of the package's include, at the address the package would have answered, so every
link to `mvp_compliance:agree` reaches it:

```python
urlpatterns = [
    path("legal/agree/", ProjectAgreementView.as_view()),
    path("legal/", include("mvp_compliance.urls")),
]
```

When `record_agreed()` raises `DatabaseError` or `RecordError`, the transaction rolls back and
the page is drawn again with `failed`, as for any failed write, described under
[Asking a person to agree](#asking-a-person-to-agree). Any other exception is not caught.
