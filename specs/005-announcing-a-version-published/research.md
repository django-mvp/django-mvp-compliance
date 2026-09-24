# Research: Announcing that a version was published

The questions the design rests on, each answered from the code on main or from Django's own source
as the project resolves it (Django 5.2.17 in the development virtualenv), never from recollection.

---

## R1 — Does anything have to be written for a failing receiver to be logged and skipped?

**Question.** FR-005 asks that a receiver's error neither undo nor hide a publication, that it be
logged, and that later receivers still run.

**Finding.** No. `Signal.send_robust()` wraps each receiver in `try`/`except Exception`, calls
`self._log_robust_failure(receiver, err)` and carries on with the next receiver
(`django/dispatch/dispatcher.py:305-309`). `_log_robust_failure` logs at `ERROR` on the
`django.dispatch` logger with `exc_info` (`dispatcher.py:263-269`).

**Consequence.** The package sends with `send_robust` and adds no handler of its own. Tests assert
the record on the `django.dispatch` logger with `caplog`.

---

## R2 — How is "sent only after it commits, never for a rollback" guaranteed?

**Question.** FR-004 and scenario 6: the receiver must see the version already in force, and must
never run for a publication that is rolled back, including one inside a caller's transaction.

**Finding.** `transaction.on_commit()` registered inside `publish()`'s `atomic()` block. Django runs
the callback once the outermost transaction commits and discards it when the block it was registered
in, or any block around it, rolls back. Called with no transaction open, the `atomic()` in
`publish()` is the outermost block, so the callback runs as it exits.

**Consequence.** Registration goes after `save()`, the last statement in `publish()` that can raise,
so a refusal never registers it. Under pytest-django's default `db` fixture every test runs inside a
transaction that never commits, so a test either captures the callbacks with
`django_capture_on_commit_callbacks(execute=True)` or uses `transactional_db` where a real commit is
the point (scenario 6).

---

## R3 — Can removing an account clear a field that `VersionQuerySet.update()` refuses?

**Question.** The publisher is frozen (FR-009), and removing the account must still succeed and
clear the foreign key (FR-013). `VersionQuerySet.update()` refuses any update touching a frozen
field on a published row.

**Finding.** Yes, because the collector never uses that queryset. `Collector.related_objects()`
builds its queryset from `related_model._base_manager` (`django/db/models/deletion.py:406`), and the
field update runs as `combined_updates.update(...)` on that queryset (`deletion.py:484-485`).
`Version.Meta` sets no `base_manager_name`, so `_base_manager` is a plain `Manager` whose queryset
has no guard. `SET_NULL` carries `lazy_sub_objs = True` (`deletion.py:73`), so the update does go
through a queryset rather than `UpdateQuery.update_batch`, but it is the plain one.

The relation is found even with `related_name="+"`: `get_candidate_relations_to_delete()` reads
`opts.get_fields(include_hidden=True)` (`deletion.py:89`).

**Consequence.** Plain `SET_NULL` is correct. The one change that would break account removal is
setting `Meta.base_manager_name` to `VersionManager`. The field's comment says so and T004 is the
test that would fail.

---

## R4 — Will `makemessages` pick up strings in `.txt` templates without a flag?

**Question.** SC-008 needs every string in both email templates in the catalog.

**Finding.** Yes. `makemessages` defaults to `["html", "txt", "py"]` when no `--extension` is given
(`django/core/management/commands/makemessages.py:360`).

**Consequence.** The templates use the `.txt` extension and the existing catalog regeneration picks
them up unchanged.
