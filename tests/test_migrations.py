"""No shipped migration writes to a published version or a recorded acceptance (D10).

``VersionManager.use_in_migrations`` and ``AcceptanceManager.use_in_migrations``
close every bulk route a migration could take, but a historical model has no
custom ``save()`` — so a data migration that called ``save()`` directly on one
would still slip past. This asserts the residue stays closed the only other
way it can be: no shipped migration performs a data write at all.
"""

import importlib
import pkgutil

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.operations.special import RunPython, RunSQL
from django.utils import timezone

import mvp_compliance.migrations as migrations_package


class TestMigrationOperations:
    """Every operation in every migration this package ships, read together."""

    def test_no_shipped_migration_uses_runpython_or_runsql(self):
        # If a legitimate data migration is ever needed, write it as a
        # RunPython that loads Version or Acceptance through the historical
        # model's own manager and calls publish()/save()/record() — never raw
        # SQL or an unguarded save() on a row this package would otherwise
        # refuse.
        for module_info in pkgutil.iter_modules(migrations_package.__path__):
            module = importlib.import_module(
                f"{migrations_package.__name__}.{module_info.name}"
            )
            migration = module.Migration
            for operation in migration.operations:
                assert not isinstance(operation, (RunPython, RunSQL)), (
                    f"{module_info.name} contains a "
                    f"{type(operation).__name__} operation — see D10 first"
                )


@pytest.mark.django_db(transaction=True)
class TestPublisherMigration:
    """Migration 0005 carries a published version forward with no publisher (Article XVI)."""

    def test_a_published_version_keeps_everything_and_records_no_publisher(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("mvp_compliance", "0004_disclosure")])
        old_apps = executor.loader.project_state(
            [("mvp_compliance", "0004_disclosure")]
        ).apps
        published_at = timezone.now()
        document = old_apps.get_model("mvp_compliance", "Document").objects.create(
            name="Terms"
        )
        version = old_apps.get_model("mvp_compliance", "Version").objects.create(
            document=document,
            number=1,
            markdown="Wording",
            html="<p>Wording</p>",
            status="current",
            published_at=published_at,
        )

        try:
            executor = MigrationExecutor(connection)
            executor.migrate([("mvp_compliance", "0005_version_publisher")])
            new_apps = executor.loader.project_state(
                [("mvp_compliance", "0005_version_publisher")]
            ).apps
            carried = new_apps.get_model("mvp_compliance", "Version").objects.get(
                pk=version.pk
            )

            assert carried.markdown == "Wording"
            assert carried.html == "<p>Wording</p>"
            assert carried.status == "current"
            assert carried.published_at == published_at
            assert carried.publisher_id is None
            assert carried.publisher_subject == ""
        finally:
            # Leave the database at the latest migration for whatever runs next.
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
