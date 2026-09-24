# Roadmap — django-mvp-compliance

**Date:** 2026-09-21

This document was designed against [GOALS.md](../GOALS.md). See also [CONTEXT.md](../CONTEXT.md)
for domain terminology and [CONSTITUTION.md](../CONSTITUTION.md) for project standards.

## Versioning

Releases are gated on goal importance rather than on a count of features.

| Version | Gate |
|---|---|
| `0.0.x` | Building toward the Essential goals. Pre-viable, expect churn, nothing published. |
| `0.1.0` | All Essential goals delivered. The minimum usable release, and the first publish. |
| `0.1.x` → `0.x` | Advancing the Expected goals, at whatever granularity the work takes. Patches are fixes. |
| `1.0.0` | All Expected goals delivered. The complete, dependable release. |
| `1.x` | Stable line: non-breaking fixes and additive features only. |
| `2.0` | Next major, where breaking changes go. |

A goal is not one minor version. Some take several, and one minor can move two. Once `1.0` ships,
a breaking change never goes out as `1.x`. It waits for the next major.

*Aspirational goals may be developed against v2 or v1 as required.*

## Essential goals: v0.1.0

Everything needed for a site to publish its legal documents and hold a record of who agreed to them.

### R1 — Documents and the versions they go through

*delivered in [#4](https://github.com/django-mvp/django-mvp-compliance/issues/4), [#5](https://github.com/django-mvp/django-mvp-compliance/issues/5) · advances G1, G2, G6*

A site keeps several legal documents at once — a privacy policy, terms, a cookie policy, whatever
else it needs — and each one is rewritten over the years without ever losing what it used to say.
A document holds a lasting identity, and a sequence of versions underneath it, each written and
reviewed before anyone sees it and then published to become the one in force.

Someone with the right permission creates a document and writes a version of it without a deploy,
a migration or a developer. A version can be worked on and looked at before it is live, and has no
standing until published. Publishing makes a version the one in force and leaves the one it
replaced intact, and a published version can never be changed afterwards, by any route the package
offers. A site runs as many documents as it needs, all managed the same way.

Serves G1, G2 and G6. Does not cover how any of it is displayed, which is R2.

### R2 — The documents, readable as pages

*feature · advances G1, G5*

A published document is something a person reads, usually by following a link in a footer, often
long before they have an account. This item gives every document an address that does not change,
gives every version an address of its own, and renders both as ordinary pages of the site rather
than as something that looks bolted on.

It comes second because a document nobody can read is not published in any sense that matters, and
because the acceptance flow in R4 needs a page to show. The superseded versions get addresses too:
somebody who agreed to the old wording is entitled to go and read it.

**Deliverables:**

- Each document has a stable, predictable address that always shows what is currently in force.
- Each version has its own permanent address, including versions that have been superseded.
- Pages take their layout, navigation and theme from the site they are installed in, with the
  project writing no templates to get that.
- Documents are written in a plain, readable markup and come out as properly structured pages.
- A project can override the presentation without forking the package.

Serves G1 and G5. Does not cover asking anybody to agree to anything.

### R3 — The record of who agreed to what

*feature · advances G2*

The point of the package. When a person agrees to a version, that fact is written down and kept:
who, which version, when. It is never revised afterwards, and somebody who agrees to a later
version has two records rather than an updated one, because both things genuinely happened.

The value of the record is only realised when somebody asks for it, which is usually a complaint,
a dispute or a regulator with a deadline. So this item includes getting the records back out in a
form a person can actually be shown, alongside the exact text they saw at the time.

A person asking for their data to be deleted does not remove these records. They are the
evidence of what that person agreed to, and a request to delete an account is R11's.

**Deliverables:**

- Agreement to a version is recorded with the person, the version and the time.
- Records are never edited, and agreeing to a later version does not overwrite an earlier record.
- Everything held about one person's agreements can be produced on request, together with the text
  they were shown.

Serves G2. Does not cover the flow that collects the agreement, which is R4.

### R4 — Asking a person to agree

*feature · advances G3, G5*

The flow itself: a signed-in person who has not agreed to what is currently in force is shown it
and asked, and what they do next is recorded. It reads as part of the site, not as an interstitial
from another application.

The interesting part is the failure. If the record cannot be written, the person has not agreed,
and they see the page again rather than carrying on with nothing behind them. Getting that right is
most of the work in this item, and it is the difference between a record you can rely on and a
record that is merely usually correct.

**Deliverables:**

- A person with something outstanding is shown it, in full, and asked to agree.
- Agreeing is recorded before they are allowed to continue, and they end up where they were going.
- A failure to record means the person has not agreed, and they are asked again.
- A person with nothing outstanding never encounters any of this.
- More than one outstanding document is handled in one sitting rather than one redirect at a time.

Serves G3 and G5. Does not cover deciding when the flow is triggered, which is R5.

### R5 — Making it apply across the site

*feature · advances G3*

R4 builds the flow. This decides when a person meets it. Applying the check across a whole site
rather than page by page is what makes it dependable, since the one view somebody forgets to
decorate is exactly where an unagreed user ends up.

Applying it everywhere immediately creates the problems every comparable package has had to solve,
and they are the substance of this item rather than an afterthought. Some paths must stay reachable
or a person gets stuck in a loop with no way out, signing out included. Some people need to be let
past — support staff, automated checks, the accounts a test suite drives. And not every document is
one you stop people over: a cookie policy is normally published and never enforced, so whether a
document is enforced at all is a decision made per document.

**Deliverables:**

- The check applies across the site without the project marking up individual views.
- Paths can be excluded, and the exclusions a person needs to escape the flow work by default.
- Named accounts, or holders of a permission, can be let past.
- Enforcement is decided per document, and publishing without enforcing is an ordinary thing to do.
- The check does not become a per-request cost on every page of the site.

Serves G3. Completes the Essential set and gates `v0.1.0`.

## Expected goals: v1.0.0

What a complete and dependable version is expected to carry.

### R6 — Telling people what changed

*resolve · advances G3*

A new version put in front of somebody who already agreed to the last one raises an obvious
question, and answering it is the difference between informed agreement and a click. Every
comparable package carries some form of this. A short summary, written by whoever prepared the
version, shown alongside it when agreement is asked for again.

Serves G3.

### R7 — Documents in more than one language

*multi-feature · advances G4*

A reader sees a document in their own language, while the canonical text stays the one their
agreement points at and the one that governs in a dispute. Translations arrive and are corrected on
their own schedule, without disturbing versions that people have already agreed to.

Serves G4.

### R8 — Cookie categories and the consent that goes with them

*multi-feature · advances G7*

Visitors decide what they will accept, grouped the way people actually decide it rather than one
cookie at a time, and the site honours the decision instead of merely recording it. Unlike
agreeing to a document this is not permanent and not tied to having an account: a visitor may
change their mind at any time, and most of them are not signed in.

Serves G7.

### R9 — A person's own record, where they expect to find it

*feature · advances G8*

Somewhere in the account area, a signed-in person can see what they have agreed to, when, and what
they currently allow, and can read again anything they agreed to. It is the visible half of a
package that is otherwise entirely invisible when it is working.

Serves G8.

### R10 — Knowing where a site stands

*feature · advances G2*

The view from the other side: which documents are in force, which versions preceded them, how many
people have agreed to what is current, and who has not. Anybody responsible for a site needs this
before a deadline arrives rather than during one.

Serves G2. Completes the Expected set and gates `v1.0.0`.

## Aspirational goals: v2.0

Genuine wants whose absence never makes the package incomplete.

### R11 — Where a person asks for their data, or for it to be deleted

*multi-feature · advances G9*

A person can ask a site for a copy of what it holds about them, or ask for their account and data to
be deleted. Both requests start from the account area, on pages this package puts there, so a
project does not build or style its own. What happens once a request is made is the project's code,
connected through a hook, because only the project knows where its data lives. The package does not
gather or delete anything itself, and a deletion leaves the acceptances in place as the evidence of
what the person agreed to.

Serves G9.
