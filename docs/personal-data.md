# How to declare what your project holds about a person

A person can only be given a copy of their data if the package knows where your project keeps
it. You tell it by writing one small class for each kind of record your project holds about a
person, such as their profile or the files they uploaded, and listing the classes in a
setting. The package holds none of this data itself and reads nothing from your models that
you have not named.

## Before you start

The page that hands a person their data asks them to confirm who they are first, using
[django-allauth](https://docs.allauth.org/)'s reauthentication. That makes django-allauth a
requirement of this feature, and of nothing else in the package. Install it with the extra:

```bash
pip install "django-mvp-compliance[personal-data] @ git+https://github.com/django-mvp/django-mvp-compliance.git"
```

Then set allauth's account app up in your project:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "allauth",
    "allauth.account",
    "mvp_compliance",
]

MIDDLEWARE = [
    # ...
    "allauth.account.middleware.AccountMiddleware",
]
```

```python
# urls.py
urlpatterns = [
    # ...
    path("accounts/", include("allauth.urls")),
]
```

## Steps

1. Write a kind for each sort of record. Subclass `PersonalData`, name the model and the
   fields to include, and say whose rows belong to the person in `get_queryset`:

   ```python
   # datasets/personal_data.py
   from django.utils.translation import gettext_lazy as _

   from mvp_compliance.personal_data import PersonalData

   from datasets.models import Dataset


   class Datasets(PersonalData):
       heading = _("Datasets you uploaded")
       description = _("Every dataset you uploaded, with its file.")
       model = Dataset
       fields = ["title", "licence", "created", "upload"]

       def get_queryset(self, user):
           return Dataset.objects.filter(owner=user)
   ```

   `get_queryset` has no default. Which field points at the person is something only your
   project knows, so a kind that does not override it raises `NotImplementedError`.

2. List the kinds by dotted path, in the order you want them shown:

   ```python
   # settings.py
   MVP_COMPLIANCE_PERSONAL_DATA = [
       "accounts.personal_data.Profile",
       "datasets.personal_data.Datasets",
   ]
   ```

3. Run `python manage.py check`. A path that cannot be imported, a field the model does not
   have and a missing allauth setup are each reported, with the id of the check that found
   them (see [The checks](#the-checks)).

The setting is optional. While it is absent, nothing of this feature exists in your project.
An empty list counts as a declaration: it declares that your project holds no personal data
of its own.

## What a value becomes

Each name in `fields` becomes a column, labelled with the model field's `verbose_name`, which
stays lazy so it is translated when it is read. The value in each row is:

- the choice's display value, for a field with `choices`,
- `str()` of the related object, for a relation,
- `None`, for an empty value (`None` or an empty string),
- a `CopiedFile`, for a `FileField` that has a file, and `None` when it has none,
- the stored value, for anything else.

A `CopiedFile` holds the file's `name`, the stored `field_file` and the `path` it takes
inside a copy: `files/<key>/<pk>/<name>`. The primary key is in the path so two records that
each have a file called `report.pdf` do not collide. The `key` is the class name in lower
case, so `Datasets` has the key `datasets`. Set `key` on the class to choose another. Two
kinds cannot share a key.

## A person who has one record

Set `single = True` when a person has one record of a kind, not a list. The profile is the
usual case:

```python
class Profile(PersonalData):
    heading = _("Your profile")
    description = _("The details on your account.")
    model = get_user_model()
    fields = ["username", "email", "date_joined"]
    single = True

    def get_queryset(self, user):
        return get_user_model().objects.filter(pk=user.pk)
```

The section carries the flag so that whatever draws it can show the record's fields as pairs
rather than a table.

## Data that is not one queryset

Override `collect` when what you hold about a person does not fit one model and one queryset.
It receives the user and returns a `PersonalDataSection`:

```python
from mvp_compliance.personal_data import PersonalData, PersonalDataSection


class Messages(PersonalData):
    heading = _("Messages")
    description = _("How many messages you sent.")

    def collect(self, user):
        sent = Message.objects.filter(sender=user).count()
        return PersonalDataSection(
            key=self.key,
            heading=self.heading,
            description=self.description,
            columns=(("sent", _("Messages sent")),),
            rows=((sent,),),
        )
```

`columns` is a tuple of `(name, label)` pairs and each row is a tuple of values in that order.
A file in a row is a `CopiedFile`, built the same way the default builds it.

## A kind drawn your own way

Set `template_name` to a template of your own to have a kind drawn by it instead of the
standard table. The section carries the name, so the code that draws a copy can tell which
kinds to hand to a template.

## The checks

`manage.py check` reports a declaration that cannot work:

| Id | Reported when |
|---|---|
| `mvp_compliance.E005` | The setting is a string or anything that is not a list or tuple. |
| `mvp_compliance.E006` | A path cannot be imported, does not name a `PersonalData` subclass, or gives a key an earlier kind already has. One error for each, naming the path. |
| `mvp_compliance.E007` | A kind with a `model` lists a field in `fields` that the model does not have. |
| `mvp_compliance.E008` | `allauth.account` is not installed, or its `AccountMiddleware` is not in `MIDDLEWARE`. |

Nothing is reported while the setting is absent.
