
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
