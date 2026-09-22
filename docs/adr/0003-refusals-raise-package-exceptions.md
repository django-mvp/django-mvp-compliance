# ADR 0003 — Refusals raise this package's own exceptions, not `ValidationError`

**Status:** accepted

## Decision

Two exception classes in `mvp_compliance.exceptions` carry every refusal this package makes:

- `PublishedVersionError` — an attempt to change or delete a version that has been published.
- `PublishError` — a publication that cannot go ahead, because the version is not a draft or because its wording renders to nothing.

Neither subclasses `django.core.exceptions.ValidationError`. Code that presents these refusals to a person translates them deliberately, at the layer where somebody is being asked to fix something.

## Why

`ValidationError` means "this input was not acceptable, tell the person and let them try again". Neither of these refusals is that.

An attempt to rewrite published wording is a breach of the guarantee the package exists to hold, not a typo. Raising `ValidationError` for it would be caught by the broad `except ValidationError` that form and admin code is built around, turned into a message beside a field, and discarded when the person edits and resubmits. The write would be refused and nobody would learn that something tried to rewrite a legal record.

A refused publication is closer to a validation failure, but it shares a catch clause with the other one, so separating them at the point they are raised is what keeps the first from being swallowed.

## Revisit if

An authoring surface finds it is translating these into form errors in more than one place with the same code. That is an argument for a shared translation helper, not for changing what the model layer raises.
