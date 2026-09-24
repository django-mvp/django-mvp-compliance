# ADR 0012 — The answer about a person is a list of sections, not a list of acceptances

**Status:** accepted

## Decision

`mvp_compliance.records.produce(subject)` returns a `PersonalRecord` whose fields are exactly
`subject` and `sections`. A `Section` is one kind of record this package holds about a person: its
heading, its entries, and the template partial that renders them. `produce()` builds two sections:
acceptances, and the versions the person published.

A further kind of record joins by being built as another section. `PersonalRecord` does not change,
the page does not change, and code that walks `record.sections` does not change. There is no
registry, no hook and no entry point: `produce()` names each kind it knows about, and nothing
outside this package can register into it.

## Why

This is the package's one answer about a person, rather than the first of several reports that each
cover a different corner of what it holds. A site fielding a request wants what is held about this
person, not what is held about them in each of the package's subsystems, and three places to look is
how a partial answer gets handed over by accident.

Cookie choices will be recorded eventually, and an account page will show a person their own consent.
Both are answers about the same person. Shaped as `{subject, acceptances}`, the answer changes shape
the day the first of those arrives, and so does every caller that walked it — the retrofit this
avoids, made worse by the fact that real records exist by then. Shaped as sections, the same
addition is a dataclass, a line in `produce()` and a partial.

The cost is one small structure, and it stops there deliberately. What is not built is anything a
host project or another application can register into: this package answers for what it holds and
says so, and an extension point would make its correctness depend on somebody else implementing
something correctly. A host project that implemented it badly would produce an answer that looks
complete and is not, which is worse than no answer at all.

A test asserts the answer's own field names, so a kind of record can only join as a section rather
than as a field somebody adds in a hurry.

## Revisit if

A kind of record turns out not to fit a heading and a list of entries — something that is genuinely
a single value rather than a sequence, or something a reader needs interleaved with acceptances by
date rather than shown beside them.
