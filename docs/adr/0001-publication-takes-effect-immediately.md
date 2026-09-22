# ADR 0001 — Publication takes effect immediately

**Status:** accepted

## Decision

`Version.publish()` puts a version in force at the moment it is called. There is no effective date, no scheduled publication and no way to prepare a version now for a date in the future.

Which version is in force is a stored fact, the row whose status is `current`. It is never a value computed from a clock at read time.

## Why

A scheduled publication means the version in force has to be worked out by comparing dates against the current time. That turns "which version was in force when this person agreed to it" from something you read into something you calculate, and a calculation can disagree with what was actually served. This package exists to keep a record that stands up as evidence, and evidence cannot rest on a derivation that might change when the rules for deriving it change.

It also weakens publishing as an act. Publishing is deliberate and one-way, and a scheduled publish separates the decision from its effect, so nobody is present at the moment the document changes.

A site that needs a notice period can announce the change and publish on the day. If scheduling is wanted later, the shape that preserves this property is a queued action that performs a real publication at the appointed time, leaving the same stored state behind — not a date field that readers have to interpret.

## Revisit if

A site needs to prepare a version that takes effect at a time when nobody will be available to publish it, and announcing the change separately is not enough. The replacement is a queue that publishes, not a date that readers evaluate.
