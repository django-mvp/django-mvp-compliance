# Progress — 002 Writing and publishing a document without a developer

Run narrative. Newest entry last.

## 2026-09-22 — S3 PLAN

Picked up off the feature queue as `ready`. Branch `002-writing-and-publishing` cut from
`origin/main` at `4f55e4d`, with the stale local branch left over from the specification run
deleted first after confirming its `specs/` content was identical to what merged as #13.

**Spec re-read against FS-001, the one feature delivered since this specification landed.** No
contradiction. FS-002's specification was written the same day and with FS-001's in hand — it names
it as a dependency throughout and adds no state to either model — and FS-001's `spec.md` has not
been touched since. The one place they meet is FR-004, where this feature's toolbar has to agree
with the allow list FS-001 applies at publication; the allow list is wider than the toolbar, which
is agreement rather than conflict, and T018 tests it in both directions.

Baseline verified green on the branch before planning: conformance, lint, typecheck, 65 tests and
build.

Research settled three things worth naming. The specification itself decides the editor — US-3
scenario 5 compares the editor's inline display with the preview, which needs an editor that has
one. EasyMDE ships no icons despite writing Font Awesome class names into every button, so the
icons are ours. And the preview reads the stored row rather than the editor's buffer, because that
is the only design under which SC-004 is true by construction.

`decisions.md` gained D8 to D12 and ADR verdicts for D1 to D7, which the specification run left
open.

## 2026-09-22 — S3R DESIGN_REVIEW

One reviewer, three lenses, one round. Verdict `request_changes`: one high, two medium, one low,
all `verified`. Every finding checked against its own stated evidence before it was applied.

Three became plan edits:

- The version form had no declared field list, and `html` — the evidence `publish()` produces —
  carries no `editable=False`, so it could have been exposed as a postable field. `VersionForm`
  now declares `fields = ["document", "markdown"]` and the admin marks the rest read-only, with a
  test asserting the form's field names are exactly those two.
- All five stories add to the same `admin.py`, so they are sequentially dependent. `tasks.md` now
  says so rather than leaving it to be discovered at convergence.
- The publish view planned to catch an exception `publish()` cannot raise. Verified against the
  model: both refusals raise `PublishError`, and the save inside `publish()` runs while the stored
  row is still a draft, so the immutability guard returns first. The second branch is gone.

The high finding is not a plan fault and was not applied. This specification's edge case about
deleting a document that holds only drafts contradicts FS-001's D8 and its accepted ADR 0002. No
requirement in this feature depends on it, the behaviour it asks for is reachable in one extra
step, and building it would mean overriding Django's deletion collector to route around the guard
that ADR exists to keep. Recorded as D13 and raised with Sam; the delivered behaviour stands
meanwhile.

## 2026-09-22T11:54:00Z · Implementer US1 · T010/T011

Did: wrote `tests/test_widgets.py::TestMarkdownEditorWidget`, asserting the rendered widget
carries a marker attribute, a `data-toolbar` of exactly the seven declared controls in order, and
none of the forbidden ones (image, embed, table, tag, raw HTML).
Verified: `poetry run pytest tests/test_widgets.py` failed on collection —
`ModuleNotFoundError: No module named 'mvp_compliance.widgets'` — the right reason, since the
widget did not exist yet.
Next: T012, the widget itself.
Watch: nothing.

## 2026-09-22T11:55:00Z · Implementer US1 · T012

Did: added `mvp_compliance/widgets.py` — `MarkdownEditorWidget(forms.Textarea)` with `TOOLBAR`
(seven `(name, gettext_lazy label)` pairs), a marker attribute and the serialised toolbar on
`data-toolbar`, and a `Media` naming the two vendored EasyMDE files before the package's own
`markdown-editor.css`/`.js`.
Verified: `poetry run pytest tests/test_widgets.py` — 5 passed. `poetry run ruff check` and
`poetry run ruff format --check` on the two new files — clean. `poetry run mypy
mvp_compliance/widgets.py` — no issues.
Next: T013/T014, the JS and CSS that make the toolbar work in the browser.
Watch: nothing.

## 2026-09-22T11:58:00Z · Implementer US1 · T013

Did: added `markdown-editor.js`. Reads `data-toolbar` off each marked textarea, maps each declared
control to EasyMDE's own built-in action, and instantiates EasyMDE with `spellChecker: false`,
`status: false`, and no preview/side-by-side/full-screen control in the toolbar it builds.
Verified: `poetry run pytest tests/test_widgets.py` — 8 passed (the two new static-asset guard
tests exercise the file's content: every declared control appears, and none of the three
preview-family EasyMDE actions do). No JavaScript runtime exists in this suite, so the file's
actual behaviour in a browser is not something a test here can prove — see the report's `concerns`.
Next: T014.
Watch: browser behaviour unverified by test; observe on the demo server once T017 gives the
widget a page to render on, and say so as observation, not proof.

## 2026-09-22T11:59:00Z · Implementer US1 · T014

Did: added `markdown-editor.css` — one inline-SVG background per toolbar button class, sized to
16px, and a rule keeping the editor's container inside the admin's `field-markdown` box.
Verified: `poetry run pytest tests/test_widgets.py` — 8 passed, including the guard asserting
every declared toolbar control has a matching `.mvp-compliance-toolbar-<name>` rule.
`poetry run ruff check`/`ruff format --check` clean; pre-commit's whitespace/format hooks ran over
both new static files (D8 only excludes the vendored ones) and made one formatting fix, re-verified
green afterwards.
Next: T015/T016, the form.
Watch: same as T013 — icon rendering itself is a demo-server observation, not a test result.

## 2026-09-22T12:03:00Z · Implementer US1 · T015/T016

Did: wrote `tests/test_forms.py::TestVersionForm` (widget used, field names exactly `document` and
`markdown`, hand-typed Markdown round-trips unchanged), then `mvp_compliance/forms.py` —
`VersionForm(forms.ModelForm)` with `Meta.fields = ["document", "markdown"]` as an explicit allow
list and `markdown` on `MarkdownEditorWidget`.
Verified: red first — `ModuleNotFoundError: No module named 'mvp_compliance.forms'` on all three.
Green after: `poetry run pytest tests/test_forms.py` — 3 passed. One test fix along the way: the
round-trip sample's trailing newline was stripped by `CharField`'s default `strip=True`, which is
ordinary Django behaviour and not a reformatting the requirement is about, so the sample lost its
trailing newline rather than the assertion being weakened. `ruff check`/`ruff format --check` clean
on both files; `mypy mvp_compliance/forms.py` clean.
Next: T017, the admin.
Watch: nothing.
