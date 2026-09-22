
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
