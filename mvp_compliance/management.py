"""Creating the documents a host project declares, after it migrates."""

from collections import Counter

from django.apps import apps as global_apps
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import DEFAULT_DB_ALIAS, router, transaction
from django.utils.translation import gettext as _

from mvp_compliance.models import Document as DocumentModel
from mvp_compliance.models import declared_documents


def declaration_faults(missing, owners) -> list[str]:
    """List what is wrong with the declarations that would create a document.

    The slug and the name are checked by the fields of the package's own
    ``Document`` model, so a declaration is held to the rules of a document
    typed into the admin.

    Args:
        missing: The declarations no document answers to, as slug to name.
        owners: The slug of the document that already has each name, by name.

    Returns:
        One message for every fault, each naming the declaration's slug and, for a
        name another document has, that document's slug. Empty when all are sound.
    """
    slug_field = DocumentModel._meta.get_field("slug")
    name_field = DocumentModel._meta.get_field("name")
    declared_names = Counter(missing.values())
    faults = []
    for slug, name in missing.items():
        problems = []
        for field, value in ((slug_field, slug), (name_field, name)):
            try:
                field.clean(value, None)
            except ValidationError as error:
                problems.extend(error.messages)
        if name != name.strip():
            problems.append(_("The name must not start or end with a space."))
        if name in owners:
            problems.append(
                _("The name already belongs to the document “%(other)s”.")
                % {"other": owners[name]}
            )
        if declared_names[name] > 1:
            problems.append(_("Another declaration gives the same name."))
        if problems:
            faults.append(
                _("Declaration “%(slug)s”: %(problems)s")
                % {"slug": slug, "problems": " ".join(problems)}
            )
    return faults


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

    Raises:
        ImproperlyConfigured: When any declaration that would create a document is
            at fault. Every fault is named, and no document is created.
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

    owners = dict(
        Document.objects.using(using)
        .filter(name__in=missing.values())
        .values_list("name", "slug")
    )
    faults = declaration_faults(missing, owners)
    if faults:
        raise ImproperlyConfigured(
            "\n".join([_("MVP_COMPLIANCE_DOCUMENTS cannot be applied:"), *faults])
        )

    with transaction.atomic(using=using):
        for slug, name in missing.items():
            Document.objects.using(using).create(slug=slug, name=name)
