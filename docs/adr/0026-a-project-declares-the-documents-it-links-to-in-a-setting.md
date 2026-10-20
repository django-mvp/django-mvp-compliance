# ADR 0026 — A project declares the documents it links to in a setting, and migrating creates them

**Status:** accepted

## Decision

`MVP_COMPLIANCE_DOCUMENTS` maps a slug to a name for each document the project's templates link to.
A `post_migrate` receiver, `mvp_compliance.management.create_declared_documents`, creates every
declared document that does not exist yet, with that slug and name and no version, in the database
being migrated. It never updates or deletes a document. When any missing declaration is at fault, it
raises `ImproperlyConfigured` naming each one and creates nothing.

A declaration carries the slug and the name and nothing else. Kind and enforcement start at the
model's defaults and belong to whoever manages the documents. A declared document's slug cannot be
changed while it is declared, whether or not a version has been published.

## Why

A template links to a document by its slug long before anyone writes it. Without a row in the
database the slug binds only the developer: the document can be created under another slug, or not at
all, and every link leads nowhere without anyone noticing. A fresh database has no documents to build
pages against.

A plain setting holds everything a declaration needs. A class per document was considered and
rejected: it would need a base class, a registry and module discovery, and a template would still
reach it by a string key. Templates already have a link that never raises, `{% url
'mvp_compliance:document' '<slug>' %}`, which is built without reading the database.

The rows are created after migrating, as Django creates permissions and the default site, because
every environment, test databases included, is migrated already. Creating them the first time
something reads them, as django-constance, django-dynamic-preferences, Wagtail's settings and
django-legaltext do, would write to the database while a page is drawn, and the documents an editor
sees would depend on which pages had been visited.

Whether people agree to a text, and whether they are stopped until they do, is a decision for whoever
manages the documents, not the developer, so neither is declared.

## Revisit if

A project needs a declared document to start as a notice or unenforced in every environment, without
an editor setting it. That would add a field to a declaration, not a second mechanism.
