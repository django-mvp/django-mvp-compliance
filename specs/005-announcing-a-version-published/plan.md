# Implementation Plan: Announcing that a version was published

**Branch**: `005-announcing-a-version-published` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-announcing-a-version-published/spec.md`

## Summary

Two fields, one signal, one function, two templates.

`Version.publish()` gains an optional `publisher` argument. It writes the publisher onto the version
twice, the same way an acceptance names its person: `Version.publisher`, a foreign key cleared when
the account is removed, and `Version.publisher_subject`, that account's primary key held as text and
never cleared. Both join the frozen fields, so every route that refuses a change to a published
version's wording refuses a change to its publisher too.

At the end of the same atomic block, `publish()` registers `version_published.send_robust` with
`transaction.on_commit`. The signal is therefore sent once, after the publication commits, and never
for one that is refused or rolled back. `send_robust` runs every receiver even when one raises, and
Django logs each error it catches, so a broken receiver neither undoes the publication nor hides it.
The admin's publish page passes `request.user` and now says the version was published.

`mvp_compliance.emails.render_publication_email(version, replaced, site_url)` renders a subject
template and a plain-text body template and returns both. It sends nothing.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.14)

**Primary Dependencies**: Django 5.2 and 6.0, django-mvp. **No new runtime dependency.** A Django
`Signal`, `transaction.on_commit`, `render_to_string`.

**Storage**: one migration (`0005_version_publisher.py`): two new columns on `Version` and the
existing check constraint `version_status_agrees_with_its_publication` widened so a draft carries no
publisher. Existing rows gain `publisher = NULL` and `publisher_subject = ""`, which reads as "no
publisher recorded" (US-2 scenario 5). No row is rewritten beyond the column defaults.

**Testing**: pytest with pytest-django, `tests/settings.py`, SQLite. Factories per Article X. The
signal is asserted through `django_capture_on_commit_callbacks(execute=True)` for the committed
case and a `transaction.atomic()` block that raises for the rolled-back case. `caplog` on the
`django.dispatch` logger for FR-005.

**Target Platform**: a Django project that has installed django-mvp.

**Project Type**: installable Django application. The admin gains a visible column and field, so
the diff is walked through on the demo project before the merge gate.

**Constraints**: Article XII (the publisher is frozen with the rest of a published version),
Article XIV (the email and docs name no regulation and claim no compliance), Article XV (the
publisher is new personal data about staff: justified at the field, named in the CHANGELOG, never
widened to a name or an email address), Article XV's no-outbound-request rule (FR-007: nothing is
sent by the package).

**Scale/Scope**: two fields, one migration, one signal module, one email module, two email
templates, admin display changes, three stories, 24 functional requirements.

## Constitution Check

Read before planning and re-checked after the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every scenario is an assertion about a receiver's calls, a stored field or a rendered string. The failing test comes first on every task | Pass |
| II Simplicity | Django's own signal, `on_commit` and `send_robust`. No dispatcher, no settings, no email backend call | Pass |
| III Anti-Abstraction | One function for the email, not a class hierarchy of messages. The override route is Django's template loader, which needs no code | Pass |
| IV Integration-First | The signal's argument list is the contract a host project codes against. It is fixed in US-1's first task and documented in the same story | Pass |
| V Security & data-safety | The body is plain text rendered with autoescape off on purpose, and it is never served as HTML. The subject is collapsed to one line, which is also what stops header injection through a document name | Pass |
| VI Documentation | `docs/announcing.md` is new and linked from the README. `docs/models.md` gains the publisher. CHANGELOG gains an Added entry naming the new personal data | Pass |
| VII Dependency discipline | No new runtime dependency | Pass |
| VIII Internationalization | Every new `verbose_name`, `help_text`, admin label, message and template string wrapped. The shipped `en` catalog regenerated. `.txt` is among `makemessages`' default extensions (`django/core/management/commands/makemessages.py:360`), so SC-008 needs no flag | Pass |
| IX Data-model conventions | `publisher` is a foreign key (automatic index). `publisher_subject` is `db_index=True`: it is the lookup a project uses to find what one removed account published, the same path `Acceptance.subject` serves. Both carry `verbose_name` and `help_text` | Pass |
| X Test structure | Tests mirror the source tree. Sending is `publish()`'s behaviour, so it is tested in `tests/test_models.py`; `signals.py` holds a declaration only. `tests/test_emails.py` mirrors `emails.py`. No new factory: a published version with a publisher is built by calling `publish(publisher=...)` on a `VersionFactory` draft | Pass |
| XI Cohesion | One module-level function in `emails.py` with no siblings, which the article's exception covers. The publisher's display text is a model property, not a helper taking a version | Pass |
| XII Immutable publication | The publisher joins `PUBLISHED_FROZEN_FIELDS`, so `save()` and the queryset's `update()` refuse it exactly as they refuse the wording | Pass |
| XIII Stored output is the evidence | Untouched. The email links to the version and does not carry its wording | Pass |
| XIV Mechanics, not compliance | The email says a version was published and by whom. It names no regulation, and no docs line claims announcing a version satisfies anything | Pass |
| XV Personal data | The account's primary key and nothing else (FR-014). Justified in the field's `help_text` and in the CHANGELOG entry | Pass |
| XVI Compatibility | `publish()` gains an optional keyword argument, so every existing caller is unchanged. The migration adds columns and carries every existing version forward | Pass |

## Design

### The publisher (US-2)

On `Version`, after `published_at`:

```python
publisher = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    verbose_name=_("publisher"),
    help_text=...,          # who put this version in force; null for a draft, for a version
                            # published from code with nobody named, and once the account is removed
    null=True,
    blank=True,
    editable=False,
    on_delete=models.SET_NULL,
    related_name="+",
)
publisher_subject = models.CharField(
    _("publisher subject"),
    max_length=255,
    blank=True,
    default="",
    editable=False,
    db_index=True,
    help_text=...,          # the publisher's primary key as text, written once at publication;
                            # what lets the version say "an account since removed" after the
                            # foreign key is cleared. Empty when nobody was recorded
)
```

- `related_name="+"`: nothing in the package walks from a user to the versions they published, and
  a reverse accessor on the host project's user model is a name this package would own forever.
  The deletion collector still finds the relation (`get_candidate_relations_to_delete` reads
  hidden fields, `django/db/models/deletion.py:89`).
- `SET_NULL`, not the `keep_or_remove_acceptances` callable: removing an account must never remove a
  version (FR-013), so there is no setting to read.
- **Account removal goes through the base manager.** The collector updates through
  `related_model._base_manager` (`deletion.py:406`, `:485`), which is a plain `Manager` because
  `Version.Meta` sets no `base_manager_name`. That is what lets removal clear a frozen field on a
  published row. Setting `base_manager_name` to `VersionManager` would put `VersionQuerySet.update()`
  in the collector's path and make account removal raise. The field's comment says so, the same
  caution ADR 0008 records for acceptances.
- `PUBLISHED_FROZEN_FIELDS` gains `"publisher"` and `"publisher_subject"`. `frozen_field_keys()`
  already adds each field's attname, so `publisher_id` is caught by `update()` too.
- The check constraint `version_status_agrees_with_its_publication` gains, on its draft branch,
  `publisher__isnull=True, publisher_subject=""`. The published branch is unchanged, because a
  published version may have no publisher.

`publish(self, publisher=None)`: inside the existing atomic block, beside `published_at`:

```python
self.publisher = publisher
self.publisher_subject = "" if publisher is None else Acceptance.subject_of(publisher)
self.save(update_fields=["status", "published_at", "html", "publisher", "publisher_subject"])
```

`Acceptance.subject_of()` is reused rather than a second `str(user.pk)`, because the identifier a
version holds and the one an acceptance holds must never disagree about who a person is. Its
docstring widens to say so.

`Version.publisher_display` (property), used by the admin and the email:

| State | Returns |
|---|---|
| draft | `None` (the admin shows its empty value) |
| `publisher_id` set | `str(self.publisher)`, the way the admin names an account |
| `publisher_id` null, `publisher_subject` set | `_("An account since removed")` |
| both empty | `_("No publisher recorded")` |

Never the removed account's subject: FR-013 says it "names nobody".

**Admin (FR-010, FR-012).**

- `VersionAdmin.publish_view` calls `version.publish(publisher=request.user)` and, on success,
  `messages.success(...)` saying the version is now in force. (The message itself belongs to US-1,
  scenario 7; US-2 only passes the publisher.)
- `VersionAdmin`: a `published_by` display method (`description=_("Published by")`) in
  `readonly_fields` right after `published_at`, and in `list_display` right after `published_at`.
  `list_select_related = ["document", "publisher"]` so the column costs no query per row.
- `DocumentAdmin`: a `published_by` column right after `in_force_since`, read from the prefetched
  version in force. The `Prefetch` queryset becomes
  `Version.objects.current().select_related("publisher")` so the count stays fixed.

### The announcement (US-1)

`mvp_compliance/signals.py`:

```python
#: Sent once a version is published and the publication has committed.
#: Sender: the ``Version`` class. Arguments: ``version`` (the version now in force),
#: ``publisher`` (the user who published it, or ``None``), ``replaced`` (the version it
#: superseded, or ``None`` for a document's first).
version_published = Signal()
```

In `publish()`, `current` is already read under the lock. After the `update()` that supersedes it,
set `current.status = self.Status.SUPERSEDED` on that instance so the receiver is not handed a stale
standing. Then, still inside the atomic block and after `save()`:

```python
transaction.on_commit(
    partial(
        version_published.send_robust,
        sender=Version,
        version=self,
        publisher=publisher,
        replaced=current,
    )
)
```

- Registered after the last line that can raise, so a refusal never registers it (FR-003).
- Registered inside the atomic block, so a savepoint or outer transaction rolled back discards it
  (FR-004). Called outside any transaction, the block commits at its own exit and the callback runs
  before `publish()` returns.
- `send_robust` catches `Exception` from each receiver, logs it on `django.dispatch` with the
  traceback, and runs the rest (`django/dispatch/dispatcher.py:263-269`, `:305-309` in the resolved
  Django 5.2.17). That is FR-005 whole, with no code of the package's own.

### The email (US-3)

`mvp_compliance/emails.py`:

```python
def render_publication_email(version, replaced, site_url) -> tuple[str, str]:
    """Render the announcement for the people running the site. Sends nothing."""
```

- Context: `version`, `replaced`, `admin_url` (`site_url.rstrip("/")` +
  `reverse("admin:mvp_compliance_version_change", args=[version.pk])`).
- Templates `mvp_compliance/email/version_published_subject.txt` and
  `mvp_compliance/email/version_published_body.txt`, both through `render_to_string`, so the app
  template loader lets a project template at the same path win (FR-021) and the active language
  applies (FR-020).
- Both templates wrap their text in `{% autoescape off %}`: plain text, never served as HTML.
- The subject is returned as `" ".join(rendered.split())`, which is one line whatever the document is
  called (FR-019, SC-007).
- The body names the document, `version.number`, `version.publisher_display`, `version.published_at`
  through the `date` filter, and either `replaced.number` or a first-version sentence.
- It takes `version` and `replaced` because those are the two values from the signal it needs. The
  publisher is read from the version, which holds it, rather than passed a second time.

A receiver that sends it is four lines, which is SC-006 and the documentation example:

```python
@receiver(version_published)
def tell_the_site_owners(sender, version, replaced, **kwargs):
    subject, body = render_publication_email(version, replaced, site_url="https://example.com")
    send_mail(subject, body, None, ["owners@example.com"])
```

### Documentation

- `docs/announcing.md` (new): the signal, when it is sent and when it is not, every argument
  (FR-023), what happens when a receiver fails, the email function and the receiver above, and how to
  override the templates. Linked from the README's documentation list.
- `docs/models.md`: *Publishing* gains the `publisher` argument, the two fields and the three things
  `publisher_display` can say.
- `docs/authoring.md`: *Publishing* says the admin records who published, and the lists show it.
- `CONTEXT.md`: **Publisher** (FR-024).
- `CHANGELOG.md` `[Unreleased]`: Added entries for the signal and the email, and a plain-language
  entry naming the new personal data (Article XV).

## Stories and order

The stories run in sequence on one branch, **US-2 first**. The signal carries the publisher, and the
publisher does not exist until US-2 writes it. US-3 renders `publisher_display`, which US-2 adds.

| Order | Story | Touches |
|---|---|---|
| 1 | US-2 A version records who published it | `models.py`, `admin.py`, migration `0005`, `docs/models.md`, `docs/authoring.md`, `CONTEXT.md`, CHANGELOG |
| 2 | US-1 A project hears about every publication | `signals.py` (new), `models.py` (`publish()` only), `admin.py` (`publish_view` message), `docs/announcing.md` (new), README, CHANGELOG |
| 3 | US-3 A ready-made email | `emails.py` (new), two templates, `tests/locale/` test catalog, `tests/settings.py`, `docs/announcing.md`, CHANGELOG, `en` catalog |

## Complexity Tracking

| Addition | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| `publisher_subject` beside the foreign key | FR-013: after the account is removed the version must still tell "an account since removed" from "nobody recorded" | A foreign key alone reads the same null in both cases, which is exactly the ambiguity FR-013 forbids |
| A test-only translation catalog under `tests/locale/` | US-3 scenario 7 needs a language other than English with a catalog, and the package ships English only | Patching `gettext` would prove the mock was called, not that the template strings are translatable |

## Outside this plan

`records.produce()`, the answer about a person, does not list the versions a member of staff
published. The answer covers consent, and publishing is staff work (decisions.md D4, ADR 0017).
