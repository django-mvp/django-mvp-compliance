# Producing everything held about a person

One page, in the Django admin, that assembles everything this package holds about
one named person and hands it over in full.

## Where it is

**Compliance → Everything held about a person**, at
`/admin/mvp_compliance/disclosure/`. It is a `GET` — asking the question changes
nothing, so asking it twice gives the same answer back — and it is the only route
this package adds for producing one. There is no download and no management
command: every route this act is reachable by needs its own permission test, and
each one adds is another to keep green.

## The permission

Reaching the page needs `mvp_compliance.produce_disclosure`, and nobody holds it
until somebody grants it. A freshly created account holds it in neither the
ordinary case nor the staff one — this is deliberate, not an oversight to route
around.

Every other permission this package defines, including the routine
`view_disclosure`/`add_disclosure`/`change_disclosure`/`delete_disclosure` Django
creates for the model behind the page, grants nothing here. Producing this answer
hands over one person's consent history, which is a different level of trust from
writing or publishing a document, so it has its own gate rather than riding on an
existing one.

A refusal looks the same whichever way it happens — not signed in, signed in and
not staff, or staff without the permission — and the same whether or not the named
person has any records at all. Nothing about the person is read until the
permission check has already passed.

```python
# settings.py, or wherever permissions are granted
from django.contrib.auth.models import Permission

user.user_permissions.add(
    Permission.objects.get(
        content_type__app_label="mvp_compliance", codename="produce_disclosure"
    )
)
```

## Naming a person

The page asks for free text, not a picker, because a record can outlive the
account it names. What is typed is resolved in order:

1. An account whose login name matches exactly.
2. Otherwise, an account whose email address matches, case-insensitively — only
   when exactly one account matches.
3. Otherwise, the text itself, as the identifier the records carry.

The third case is what makes it possible to ask about somebody whose account has
since been removed: there is no row left to look up, but their acceptances still
carry the identifier they were recorded under. The answer names the subject it was
produced for, so whichever reading was taken is visible on the page.

## What the answer contains

Every acceptance held for that person: the document, the version accepted, when it
happened, and the wording that version carried at publication — never wording
produced again at this point, so an answer never shows something the person was
never actually served. A person the package holds nothing about gets a page
saying so, which is a normal result rather than an error.

## What it does not do

Nothing here is recorded. Producing an answer leaves no trace of having been
asked, and the page carries no add, change or delete control — it is read-only in
every sense, and the admin index only shows it to somebody holding the
permission.
