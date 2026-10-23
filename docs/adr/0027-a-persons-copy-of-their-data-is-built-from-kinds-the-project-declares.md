# ADR 0027 — A person's copy of their data is built from kinds the project declares, and is whole or not given

**Status:** accepted

## Decision

The copy a signed-in person downloads from **Your data** holds what the project lists in
`MVP_COMPLIANCE_PERSONAL_DATA`: dotted paths to subclasses of
`mvp_compliance.personal_data.PersonalData`, in the order listed, followed by the package's own
section, the documents the person agreed to. The package reads nothing of the project's data that a
declared kind does not hand it.

The page and its route exist only while the setting is set. An empty list is a declaration: the
project is saying the agreements are everything it holds about a person.

Every kind is collected, and every file and every kind's own template opened or rendered, before
the copy is handed over. If any of them fails, the person gets no copy, and the failure is logged
naming the kind. A copy carries the time it was made.

This applies to the person's own copy only. The admin page staff use to produce what the package
holds about a person stays as ADR 0012 has it, with nothing a project can add to it.

## Why

A person asking for a copy of their data is asking about everything a site holds, and only the
project knows where that is. The package's constitution says a project's data is reached through a
documented hook the project implements, and never gathered by the package itself. A settings list of
classes is that hook in the shape Django developers already know from `AUTH_PASSWORD_VALIDATORS` and
generic views. Registering kinds from each app's `ready()` was rejected, because it would let any
installed app add itself to every project's copy and make the order depend on import order.

ADR 0012 refused any outside contribution to the answer about a person, because a project that
implemented one badly would produce an answer that looked complete and was not. A person's copy
cannot avoid outside contributions. It handles that risk instead by giving nothing when any part
fails, and by naming every kind it holds without claiming to be everything. Requiring a declaration
before the page exists means a copy holding only the agreements is never offered by accident as if it
were everything the site holds.

ADR 0013 keeps the staff answer free of a production time so that two readings of the same records
are equal. A person's copy is their own file, and somebody holding two of them needs to know which
is newer. The agreements section inside it still carries only the times stored on the acceptances.

## Revisit if

The copy is prepared in the background (#116), which needs a finished copy to be kept somewhere
until it is downloaded, or a kind of data turns up that cannot be read for one person at a time.
