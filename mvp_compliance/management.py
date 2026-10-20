"""Creating the documents a host project declares, after it migrates."""

from django.apps import apps as global_apps
from django.db import DEFAULT_DB_ALIAS, router, transaction

from mvp_compliance.models import declared_documents


def create_declared_documents(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=global_apps,
    **kwargs,
) -> None:
    """Create each declared document that does not exist yet.

    Connected to ``post_migrate``. A document is created with its slug and name
    only: no version, and the model's own kind and enforcement. One that already
    has the declared slug is left exactly as it is, and a document whose
    declaration was dropped is never removed.

    Args:
        app_config: The app whose migrations have just run.
        verbosity: Accepted from ``post_migrate``; unused.
        interactive: Accepted from ``post_migrate``; unused.
        using: The alias of the database that was migrated.
        apps: The app registry to read the model from, historical during a migration.
        **kwargs: Anything else ``post_migrate`` sends.
    """
    try:
        Document = apps.get_model("mvp_compliance", "Document")
    except LookupError:
        return
    declared = declared_documents()
    if not declared or not router.allow_migrate_model(using, Document):
        return

    existing = set(Document.objects.using(using).values_list("slug", flat=True))
    missing = {slug: name for slug, name in declared.items() if slug not in existing}

    with transaction.atomic(using=using):
        for slug, name in missing.items():
            Document.objects.using(using).create(slug=slug, name=name)
