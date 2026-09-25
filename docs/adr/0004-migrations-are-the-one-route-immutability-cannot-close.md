# ADR 0004 — Migrations are the one route immutability cannot close, and it is closed by not writing one

**Status:** accepted

## Decision

`VersionManager` is declared `use_in_migrations = True`, so a historical `Version` model rebuilt inside a migration gets the same manager and queryset, and the bulk write routes refuse there too.

One route stays open: a data migration shipped by this package calling `save()` on a historical instance. It is closed by this package shipping no such migration, and by a test asserting that no migration it ships contains a `RunSQL` operation, or a `RunPython` operation the test does not name.

The test names one. Migration `0006` clears the number from every draft (ADR 0018). It writes through the historical model's own manager, whose `update()` refuses if any row it touches is published, and never calls `save()`. A second test runs it over a published version and a draft and checks that the published version comes through unchanged.

No database triggers.

## Why

Django rebuilds historical models from migration state. A historical model does not carry the real model's `save()` or `delete()`, so no model-level guard reaches code running inside a migration. Declaring the manager for use in migrations recovers the queryset guards, which covers `update()` and queryset `delete()`, but nothing recovers `save()`.

Closing that last route properly means putting the rule in the database as a trigger. That means writing and maintaining the DDL for every backend a host project might bring, and having no answer for one that is not covered. The rule would then live in a place migrations themselves have to work around.

The route that remains is not one the package offers anyone. It is reachable only by code inside this repository, written by the people who set the rule, reviewed like any other change, and covered by a test that fails the moment someone adds a data migration it does not name.

It is written down here rather than left to be discovered, because an immutability claim with an unstated exception is worse than one with a stated exception.

## Revisit if

This package genuinely needs to ship another data migration. The test will fail, which is the point: the migration then has to be shown not to write to a published version, and this ADR gets the exception recorded rather than assumed.
