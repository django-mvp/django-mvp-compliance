# ADR 0028 — A person confirms who they are with django-allauth before they reach their copy

**Status:** accepted

## Decision

`PersonalDataView` is guarded by `allauth.account.decorators.reauthentication_required` on `get`
and `post`. Opening **Your data** sends a person who has not confirmed recently to allauth's own
confirmation page and brings them back. django-allauth is an optional dependency, installed with the
extra `personal-data`. Without `allauth.account` the page is not found, and `manage.py check`
reports a declared copy on a site without allauth's account app and middleware
(`mvp_compliance.E008`).

The package follows allauth's judgement of who has to confirm and adds no rule of its own. An
account with no password and no second factor, such as one that signs in only through another
provider, has nothing to confirm with, and allauth lets it through. So does this page.

## Why

A copy hands over everything a site holds about a person in one file, so somebody who has found a
signed-in browser should not be able to take it. A confirmation page of the package's own would be a
second password form, without allauth's rate limits, its second factors, or its record of when a
person last confirmed. Projects on django-mvp sign in through django-mvp-accounts, which is built on
allauth, so its confirmation is already the one people see on the site's other sensitive pages, such
as adding a second factor.

Refusing a copy to an account with nothing to confirm with was considered and not taken. It would
lock such a person out of their own data until they set a password, and it would be stricter than
the site's own handling of its sensitive pages.

## Revisit if

allauth changes how it decides who has recently confirmed, or a project needs this page without
allauth.
