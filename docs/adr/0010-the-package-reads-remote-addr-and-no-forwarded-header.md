# ADR 0010 — The optional address evidence reads `REMOTE_ADDR` and no forwarded header

**Status:** accepted

## Decision

An acceptance holds the person, the version and the time. It holds the address a request came from
only when the host project sets `MVP_COMPLIANCE_RECORD_IP_ADDRESS = True` and passes a request to
`Acceptance.objects.record()`. The default is off.

When it is on, the package reads `request.META["REMOTE_ADDR"]` and nothing else. It does not read
`X-Forwarded-For`, and it does not read any other forwarded header, under any circumstance or
configuration. A project behind a proxy is responsible for making `REMOTE_ADDR` correct.

## Why

An address is personal data about somebody who did not ask for it to be kept, so holding it is the
host project's decision to make rather than this package's to assume. Some sites genuinely need it,
because it makes a record harder to dispute. Defaulting it off and requiring both the setting and a
request means nothing is collected by accident.

The refusal to read forwarded headers is the part worth recording, because reading one is a wrong
answer that looks right. Behind a proxy, `REMOTE_ADDR` is the proxy, and the client's address is in
`X-Forwarded-For`. But that is a header, which means the client sets it. A package that reads it
when present has an evidence field that the person the evidence is about can fill in themselves,
which is worse than holding nothing — it looks like corroboration and is not.

Resolving it correctly needs facts this package cannot have: how many proxies stand in front, which
of them are trusted, and whether the header can be spoofed past them. Only the deployment knows.
Making `REMOTE_ADDR` correct behind a proxy is ordinary Django deployment work with well-understood
middleware, and that is where the knowledge lives.

## Consequences

Turning the setting on or off never changes a record that already exists, because an acceptance is
never edited. Records made before it was on hold no address; records made while it was on keep what
they held after it is turned off again. That is a property of immutability rather than anything this
feature implements.

Recording with the setting on but no request supplied succeeds and holds no address, so a management
command or a shell session does not have to invent a value.

A project that deploys behind a proxy without configuring `REMOTE_ADDR` correctly and turns this
setting on will record the proxy's address. That is a deployment error with a visible, uniform
symptom, which is a better failure than silently trusting a client-supplied value.
