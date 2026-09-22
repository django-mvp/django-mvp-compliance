# ADR 0006 — `VersionManager` forwards queryset methods explicitly

**Status:** accepted

## Decision

`VersionManager` subclasses `models.Manager`, overrides `get_queryset()` to return a `VersionQuerySet`, and carries a one-line forwarding method for every `VersionQuerySet` method a caller reaches through a manager.

It is not built with `models.Manager.from_queryset(VersionQuerySet)`.

**Adding a method to `VersionQuerySet` is therefore two steps.** Add it to the queryset, then add its forwarder to the manager. Without the second step the method works on `Version.objects.all().thing()` and fails on `document.versions.thing()`, which is the route every caller actually uses.

## Why

`from_queryset()` builds a class at runtime, and mypy rejects a dynamically built class as a base: `Unsupported dynamic base class "models.Manager.from_queryset"`. No annotation resolves it, because the base class itself is what mypy will not follow. Silencing it would leave the manager's whole public surface unchecked, in a file where every other name is checked.

Overriding `get_queryset()` alone is not enough. Django generates manager wrappers for the queryset methods it knows about, so `update()`, `delete()` and `filter()` reach the custom queryset through the override — but a method that exists only on `VersionQuerySet` has no generated wrapper and is not forwarded.

The explicit forwarders cost one line each and keep the manager's surface type-checked. The trap they leave is the two-step above, which is why it is stated here and in the class docstring, and why the tests exercise `document.versions.published()` rather than `Version.objects.published()`.

## Revisit if

Django's type stubs or mypy gain support for `from_queryset()` as a base class, or the number of forwarders grows past the point where writing them by hand is reliable.
