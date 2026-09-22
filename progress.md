
## 2026-09-22T15:00:00+02:00 · Implementer US-4 · T040
Did: Added `TestPublish` to `tests/test_admin.py` with two permission tests for the not-yet-built publish address.
Verified: `poetry run pytest tests/test_admin.py::TestPublish -x` failed with `NoReverseMatch` (RED, correct reason).
Next: T041.
Watch: nothing.

## 2026-09-22T15:05:00+02:00 · Implementer US-4 · T041
Did: `VersionAdmin.get_urls()` adds `<pk>/publish/`, wrapped in `admin_site.admin_view`; `publish_view` checks `publish_version` and otherwise returns an empty stub response for now. Registered "version publish" in `DRAFT_PRIVACY_ADDRESSES` per D14 so the three-caller sweep in `TestDraftPrivacy` covers it without a second walk.
Verified: `poetry run pytest tests/test_admin.py -q` — 39 passed.
Next: T042.
Watch: `publish_view`'s GET/POST bodies are still placeholders; T043 and T045 replace them.

## 2026-09-22T15:20:00+02:00 · Implementer US-4 · T042
Did: Added `test_a_get_confirms_and_publishes_nothing`, asserting the confirmation names the document and version, shows the live rendering, and states the consequence.
Verified: `poetry run pytest tests/test_admin.py::TestPublish::test_a_get_confirms_and_publishes_nothing -x` failed on the content assertion against the stub's empty body (RED, correct reason).
Next: T043.
Watch: nothing.

## 2026-09-22T15:25:00+02:00 · Implementer US-4 · T043
Did: `publish_confirmation.html` — names the version, shows the rendering about to go live, states plainly that the wording cannot be changed and a correction is another version, offers a Publish control and a Back link. `publish_view`'s GET branch now renders it.
Verified: `poetry run pytest tests/test_admin.py::TestPublish -q` — 3 passed.
Next: T044.
Watch: nothing.

## 2026-09-22T15:30:00+02:00 · Implementer US-4 · T044
Did: Added `test_a_post_publishes_and_declining_does_not`.
Verified: failed with `assert 200 == 302` against the still-stub POST branch (RED, correct reason).
Next: T045.
Watch: nothing.

## 2026-09-22T15:35:00+02:00 · Implementer US-4 · T045
Did: `publish_view`'s POST branch calls `Version.publish()` in a `try`, catches `PublishError`, adds its message with `messages.error`, and always redirects to the change page.
Verified: `poetry run pytest tests/test_admin.py::TestPublish -q` — 4 passed.
Next: T046.
Watch: only `PublishError` is caught, per D7 — `PublishedVersionError` cannot be raised by `publish()`.

## 2026-09-22T15:45:00+02:00 · Implementer US-4 · T046
Did: Added `test_both_refusals_reach_the_author_as_a_message` covering an empty-rendering draft and an already-published version.
Verified: `poetry run pytest tests/test_admin.py::TestPublish::test_both_refusals_reach_the_author_as_a_message -x` passed immediately (T045 already implements the redirect path).
Next: T047.
Watch: nothing.

## 2026-09-22T15:50:00+02:00 · Implementer US-4 · T047
Did: Added `test_saving_a_draft_publishes_nothing`, checking the change form's save, the get response body and the changelist body for any publish control.
Verified: passed immediately — nothing in the admin currently offers publication outside the confirmation page.
Next: T048.
Watch: nothing.

## 2026-09-22T15:55:00+02:00 · Implementer US-4 · T048
Did: Added `test_a_published_version_has_no_editable_form`.
Verified: failed on `name="markdown"` still present (RED, correct reason — the change form was still fully editable).
Next: T049.
Watch: nothing.

## 2026-09-22T16:00:00+02:00 · Implementer US-4 · T049
Did: `VersionAdmin.has_change_permission()` returns `False` for a published object, so Django serves its own read-only detail page.
Verified: `poetry run pytest tests/test_admin.py -q` — 44 passed. Along the way, corrected T048's `type="submit"` assertion (it was tripping on the site chrome's unrelated log-out button) to `name="_save"`, the admin's actual save control.
Next: T041a (see decisions.md), then T049a/T049b.
Watch: nothing.

## 2026-09-22T16:05:00+02:00 · Implementer US-4 · T041a (unnumbered — decisions.md)
Did: Added a Publish link to the change form's object tools, matching T035's forward reference and the pattern of the existing Preview link. Visible only for a draft to a caller holding `publish_version`.
Verified: `poetry run pytest tests/test_admin.py -q` — 46 passed.
Next: T049a.
Watch: flagged in the completion report's concerns — this addition has no task ID of its own.

## 2026-09-22T16:15:00+02:00 · Implementer US-4 · T049a
Did: Added `catalog_entries()`, `python_translatable_strings()`, `template_translatable_strings()` helpers, parsing the shipped `.po` catalog and the package's own `.py`/`.html` source rather than a hand-kept list. Added `TestUserFacingStrings::test_nothing_claims_compliance`.
Verified: `poetry run pytest tests/test_admin.py::TestUserFacingStrings -x` — `test_nothing_claims_compliance` passed immediately; `test_every_string_is_translatable` failed, showing every string this story (and two earlier ones) had shipped without ever running `makemessages` on it.
Next: T049b.
Watch: nothing.

## 2026-09-22T16:20:00+02:00 · Implementer US-4 · T049b
Did: Ran `makemessages -l en` from `mvp_compliance/` and filled each new entry's `msgstr` to match its `msgid`, per this catalog's existing English-base convention. Cleared the fuzzy match `msgmerge` guessed between "Publish" and the pre-existing "published at". This closed a pre-existing gap: `preview.html`'s and `widgets.py`'s strings had never been added to the catalog by any earlier story.
Verified: `poetry run pytest tests/test_admin.py::TestUserFacingStrings -q` — 2 passed. `poetry run pytest tests/test_admin.py -q` — 48 passed.
Next: T049c.
Watch: none of my new commands touched `mvp_compliance/apps.py`, `models.py` or `widgets.py` themselves — only their catalog entries, which is in scope (`mvp_compliance/locale/`).
