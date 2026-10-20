# Implementation Plan: Declaring the documents a site links to

**Branch**: `011-declared-documents` | **Date**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

## Summary

A setting, `MVP_COMPLIANCE_DOCUMENTS`, maps each declared slug to its name. A `post_migrate`
receiver creates every declared document that is missing, with no version, after checking every
declaration and writing nothing if one is at fault. While a slug is declared, `Document.save()`,
`DocumentQuerySet.update()` and the admin refuse to change it. No template tag, no class and no
system check are added.

## Technical context

Python 3.12+, Django 5.2 to 6.1, as the CI matrix says. No new dependency. Tests with pytest and
pytest-django, settings `tests.settings`.

## Constitution check

- **Article I, testing**: every task that changes behaviour starts from a failing test.
- **Article II, simplicity, and III, anti-abstraction**: one setting, one receiver, one reader, one
  exception. No registry, no wrapper class (decisions.md D1).
- **Article IX, data-model conventions**: no field and no migration. Rows are created through the
  historical model in the receiver.
- **Article XI, records are never written to**: the receiver creates documents only. It never
  reads or writes a version or an acceptance.
- **Article XV, compatibility**: a project that does not set the setting sees nothing change
  (FR-009).

## Design

### The setting

```python
MVP_COMPLIANCE_DOCUMENTS = {
    "privacy-policy": "Privacy policy",
    "terms-of-use": "Terms of use",
    "impressum": "Impressum",
}
```

`declared_documents()` in `mvp_compliance/models.py` returns it, an empty dict when unset, read
each time it is called.

### Creating declared documents

`mvp_compliance/management.py`, `create_declared_documents(app_config, using=DEFAULT_DB_ALIAS,
apps=global_apps, **kwargs)`, connected in `MvpComplianceConfig.ready()` with
`post_migrate.connect(..., sender=self)`:

1. Return when nothing is declared, when `apps` has no `mvp_compliance.Document`, or when
   `router.allow_migrate_model(using, Document)` is false.
2. Find the declarations whose slug no document has.
3. Check each of those: the slug and the name through the global `Document` fields' `clean()`, a
   name another document has under another slug, and a name two declarations share. Collect every
   fault.
4. Any fault → raise `ImproperlyConfigured` listing them, each naming the declaration's slug and,
   for a clash, the other document's slug. Nothing is written.
5. Otherwise create the missing documents in one `transaction.atomic(using=using)`, through the
   historical model, with slug and name only.

### The slug lock

- `DeclaredDocumentError` in `mvp_compliance/exceptions.py`.
- `Document.save()`: when it writes the slug and the stored slug differs, raise
  `DeclaredDocumentError` if the stored slug is declared, before the existing published check.
- `DocumentQuerySet.update()`: with `slug` in the update, raise `DeclaredDocumentError` if any row
  in the queryset has a declared slug, before the existing published check. `bulk_update()` goes
  through it.
- `DocumentAdmin.get_readonly_fields()`: add `slug` when the document's slug is declared.

### Documentation

- `docs/models.md`: a section *Declaring documents* (the setting, when documents are created, what
  is and is not declared, a link to a document before its first version, changing and removing a
  declaration, the refusal on a conflict), and *When the slug is fixed* gains the declared case
  and `DeclaredDocumentError`.
- `docs/pages.md`: the footer example says a declared document's address can be linked before
  anything is published.
- `README.md`: the setting among the others.
- `CONTEXT.md`: *Declared document*, and *Slug* says when a declared slug is fixed.
- `CHANGELOG.md`: *Added* under Unreleased.

### The demo

`demo/settings.py` declares the privacy policy, the terms of use and the impressum. `seed_demo`
sets a found document's kind when it differs from the one it seeds.

## Project structure

```
mvp_compliance/
  apps.py            # connects the receiver
  exceptions.py      # DeclaredDocumentError
  management.py      # create_declared_documents (new)
  models.py          # declared_documents(), the slug lock
  admin.py           # read-only slug for a declared document
tests/
  test_management.py # new, mirrors management.py
  test_models.py, test_admin.py, test_exceptions.py
```

## Complexity tracking

None. Nothing here goes beyond the simplest design the specification allows.
