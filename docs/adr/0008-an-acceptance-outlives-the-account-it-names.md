# ADR 0008 — An acceptance outlives the account it names, unless the project says otherwise

**Status:** accepted

## Decision

Removing a user account does not remove that person's acceptances. Each record stays, still saying
whose it is and still pointing at the version accepted. A host project that wants the opposite sets
`MVP_COMPLIANCE_ACCEPTANCES_SURVIVE_ACCOUNT_REMOVAL = False`, and removing an account then removes
that person's acceptances with it. Under either setting, removing one account leaves every other
person's records untouched.

Three things follow from that and are part of this decision rather than separate ones.

A record names its person twice. `Acceptance.user` is an ordinary foreign key, and `subject` is that
account's primary key copied onto the record as text when it is written. The foreign key is what
gets cleared when an account goes; `subject` is what survives, so the record can still say whose it
is and can still be found among that person's others with
`Acceptance.objects.for_subject(...)`. Holding the primary key rather than a username means an
account removed and recreated under the same name inherits nothing, because it is a different
account and therefore, for this purpose, a different person.

The setting is read by a callable in the `on_delete` position, not by a signal receiver.
`on_delete` accepts any callable taking `(collector, field, sub_objs, using)` — that is all Django's
own `SET_NULL` and `CASCADE` are — and the collector invokes it at the moment a delete runs, which is
where a setting can be read. `keep_or_remove_acceptances` reads it there and delegates to whichever
of Django's own behaviours the setting names.

The field stays `null=True`. Django's system check for a missing `null=True` compares `on_delete`
against `SET_NULL` by identity, so it does not recognise a callable that only delegates to it, and
will not raise the error it would raise for the real thing.

## Why

An account being closed or tidied up is an administrative act. It is not a statement about whether
something happened. Two readings of what should follow are both defensible: keeping the records
honours the rule that an acceptance is never deleted, and removing them honours data minimisation,
because a closed account otherwise leaves personal data behind indefinitely with nobody watching it.

A genuinely two-sided question of that kind becomes a setting rather than a guess. The default is
this package's own position, which is that evidence outlives convenience. A site facing a dispute in
2029 about what somebody agreed to is not helped by a record that vanished when an administrator
tidied up an account in 2027, and losing it as a side effect of an unrelated action is the exact
failure this package exists to prevent.

The cost of that default is real and is stated rather than hidden, in the README and in
`docs/models.md`: under it, closing an account does not remove what this package holds about that
person. A project that assumed otherwise would be wrong. A project that wants one specific person's
records gone has a deliberate route to ask for it, which is a different thing from an account being
closed.

A signal receiver was the other way to reach the same behaviour. It would run beside the delete
rather than as part of it, which means a second thing to keep in step with the collector, a second
place for the rule to live, and a delete that is not one operation. The callable is the mechanism
Django already offers for exactly this position.

## Consequences

Anything reading a person's acceptance history reads it by `subject`, not by walking the user
relation, because the relation is null for everybody whose account has gone.

`Acceptance.user` being null carries one meaning and only one: the account has since been removed. It
never means the acceptor was unknown, because recording against a user with no primary key is
refused.

The configured removal deletes acceptances, which sits alongside a package that otherwise refuses
every route to deleting one. There is no contradiction in practice — the collector issues its
deletes through Django's internal query machinery rather than through the queryset whose `delete()`
is refused — but it does mean the refusal is a statement about what this package offers a caller,
not a claim that no row can ever leave the table.

Two changes together would put the collector's field update through the queryset that refuses
changes, and break account removal under the default: giving `keep_or_remove_acceptances` a
`lazy_sub_objs` attribute, and setting `Meta.base_manager_name` to the manager whose queryset carries
the guard. Neither alone does anything. A test asserts both halves.
