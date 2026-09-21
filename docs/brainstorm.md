# Brainstorm — why this package exists

Working notes from the conversation that started the repository, 21 September
2026. These are conclusions reached in discussion, not ratified decisions.
Nothing here is binding on the design.

## The problem

Legal documents on a website change on a schedule nobody controls. When a
privacy policy is a template in the repository, every wording change is a
deployment, and the only record of what the previous wording said is the commit
history — which nobody can hand to a person asking what they agreed to in March.

Two things are wanted at once:

1. Change the text without shipping code.
2. Retain, permanently and unambiguously, the version each person accepted.

## Prior art

Checked 21 September 2026, by reading the published packages and their source
rather than their summaries.

### django-termsandconditions

Actively maintained. Version 3.0 requires Python 3.12+ and Django 5.2+.

It already does more than it is usually credited with. Reading
`termsandconditions/models.py`: documents are scoped by a `slug` field, so a
site can carry a privacy policy and a cookie policy and a user agreement side
by side. `get_active(slug)` returns the current version of one of them,
`get_active_terms_list()` returns the current version of all of them, and
`get_active_terms_not_agreed_to(user)` spans every slug. Acceptance is recorded
in `UserTermsAndConditions` with an optional IP address and a timestamp.
Middleware redirects users to an acceptance page when the active version
changes, with exclusion lists, a permission to skip the check, and caching.

**Multiple documents are not a gap.** Neither is avoiding a redeploy: `text` is
a `TextField` on the model, so its content already lives in the database.

What it does not do:

- **A published version is mutable.** `text` is an ordinary editable field on
  the same row that acceptance records foreign-key to. Editing it rewrites what
  a user is recorded as having agreed to, silently, with the acceptance record
  still reading as valid. For a system whose only output is evidence, this is
  the gap that matters.
- No Markdown, and no rendered public page. The stored text is placed into an
  acceptance template.
- No draft or publish workflow. `date_active = NULL` means "never active",
  which is a null state rather than a draft. There is no preview step.
- `version_number` is a `DecimalField`, but the active version is computed as
  the most recent past `date_active`, so the number does not order anything.

### django-tos

Actively maintained, tested against Django 4.2 through 6.1. Genuinely a single
document: `TermsOfService.save()` deactivates every other row whenever one is
marked active. Two models, re-agreement prompted at login. A good fit for a site
with one document and no appetite for configuration, and not a fit here.

### django-cookie-consent

Version 1.0.0, February 2026, published from `django-commons` with trusted
publishing. Cookie groups as models, opt-in and opt-out schemes, removal of
declined cookies, and a log of accept and decline actions.

This is a healthy package solving the cookie half properly. The hard part of
cookie consent is client-side script gating, and it is not a part worth
rewriting to own it.

## Why build anyway

The honest differentiator is not the data model. It is two things:

**Immutable published versions.** Acceptance has to point at a version that
cannot be edited afterwards. This cannot be retrofitted onto another package's
model from the outside, and it is the design centre here.

**Integration.** `django-easy-icons` and `django-flex-menus` both sit alongside
capable generic alternatives, for the reason that applies here too: a project
running django-mvp wants its policy pages, its acceptance flow, its consent
banner and its account area to look and behave like the rest of the site, and to
be configured the way the rest of the site is configured. Three unrelated
packages with three admin styles and three settings namespaces do not give that.

On top of those: Markdown authoring with a real published page, a draft and
publish lifecycle, and one place in the account area showing a person everything
they have agreed to and chosen.

## Overlap, stated plainly

Documents, versioning, acceptance records and enforcement middleware all overlap
with `django-termsandconditions`. Cookie categories and consent logging overlap
with `django-cookie-consent`. A project that wants only one of those problems
solved, and does not run django-mvp, is better served by the existing packages,
and the README says so.

## Deliberately not in scope

Data subject access requests are a surface here, never an implementation. The
package can show a person what they have accepted and offer documented hooks for
export and erasure. It cannot gather or delete data it does not know about, and
claiming otherwise would be worse than not offering it.

## Left open

- Whether cookie consent is built here or composed from `django-cookie-consent`.
- Where the account-area integration lives, given the account package mounts
  integration URLs from its core app rather than letting an integration
  contribute them.

Both were left open on purpose. The package starts as one flat `mvp_compliance`
app, and the seams get drawn when a feature needs them rather than in advance.
