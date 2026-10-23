# Planning notes — FS-012

Suggestions from Sam for research and planning. Each is answered by name in `research.md`.

## N1 — Flexible for host projects, consistent for people

> This is a fairly important feature to get right so I suggest thinking carefully about what is
> required and how we can maintain flexibility while also providing a consistent UI and UX.

The direction agreed with Sam before the spec was written: each app describes what it holds about a
person, and the package presents it. A project lists its kinds in a setting, in the style of
`AUTH_PASSWORD_VALIDATORS`, each a dotted path to a class shaped like Django's generic views:

```python
MVP_COMPLIANCE_PERSONAL_DATA = [
    "accounts.personal_data.Profile",
    "datasets.personal_data.Datasets",
]


class Datasets(PersonalData):
    heading = _("Datasets you uploaded")
    model = Dataset
    fields = ["title", "licence", "created"]  # labels from verbose_name
    file_fields = ["upload"]  # copied into files/

    def get_queryset(self, user):
        return Dataset.objects.filter(owner=user)
```

Overriding `collect(user)` covers data that is not one queryset (US-2), and a `template_name`
gives a kind its own presentation in the readable part. The copy is one zip: `index.html`
readable offline, `data.json`, and `files/`. The person's identity is confirmed before the copy is
made, using allauth's reauthentication where the project has it, which mvp-accounts already wires
up. A signal fires after each copy, in the style of `version_published`.

## N2 — The same declaration should serve deletion later

The class is the one place an app says what it holds about a person. #48 (deleting an account and
its data) can add an `erase(user)` method to it, so research should check that nothing in this
design makes that awkward. Nothing for #48 is built here.

## N3 — Built on the spot now, in the background later

> The on-the-spot vs email question is something only the host project can answer. It should
> probably become a setting. We should also provide a way to turn this into a background task so
> that a server doesn't get overwhelmed for large processing requests.

That is #116. Here the copy is built in the request. The declared kinds take a user and never a
request, so #116 can run the same kinds in a background task with no change to a project's code.
