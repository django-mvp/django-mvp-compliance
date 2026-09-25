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

    #: The data migrations this package ships, each one shown by a test below
    #: to leave every published version as it was (ADR 0004).
    DATA_MIGRATIONS = {"0006_version_numbered_at_publication": "clear_draft_numbers"}

    def test_no_shipped_migration_writes_data_except_the_ones_recorded(self):
        # A new data migration loads Version or Acceptance through the
        # historical model's own manager, is added here, and gets a test
        # proving it leaves published versions and acceptances untouched —
        # never raw SQL or an unguarded save() on a row this package would
        # otherwise refuse.
        for module_info in pkgutil.iter_modules(migrations_package.__path__):
            module = importlib.import_module(
                f"{migrations_package.__name__}.{module_info.name}"
            )
            migration = module.Migration
            for operation in migration.operations:
                assert not isinstance(operation, RunSQL), (
                    f"{module_info.name} contains a RunSQL operation — see ADR 0004"
                )
                if isinstance(operation, RunPython):
                    assert operation.code.__name__ == self.DATA_MIGRATIONS.get(
                        module_info.name
                    ), f"{module_info.name} writes data — see ADR 0004 first"


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


@pytest.mark.django_db(transaction=True)
class TestNumberingMigration:
    """Migration 0006 clears a draft's number and leaves published ones (Article XVI)."""

    def test_a_published_version_keeps_its_number_and_a_draft_loses_one(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("mvp_compliance", "0005_version_publisher")])
        old_apps = executor.loader.project_state(
            [("mvp_compliance", "0005_version_publisher")]
        ).apps
        OldVersion = old_apps.get_model("mvp_compliance", "Version")
        published_at = timezone.now()
        document = old_apps.get_model("mvp_compliance", "Document").objects.create(
            name="Terms"
        )
        superseded, current, draft = (
            OldVersion.objects.create(
                document=document,
                number=number,
                markdown=f"Wording {number}",
                html=f"<p>Wording {number}</p>" if status != "draft" else "",
                status=status,
                published_at=published_at if status != "draft" else None,
                publisher_subject="7" if status != "draft" else "",
            )
            for number, status in ((1, "superseded"), (2, "current"), (3, "draft"))
        )

        try:
            executor = MigrationExecutor(connection)
            executor.migrate(
                [("mvp_compliance", "0006_version_numbered_at_publication")]
            )
            new_apps = executor.loader.project_state(
                [("mvp_compliance", "0006_version_numbered_at_publication")]
            ).apps
            NewVersion = new_apps.get_model("mvp_compliance", "Version")
            carried = {v.pk: v for v in NewVersion.objects.all()}

            assert carried[superseded.pk].number == "1"
            assert carried[current.pk].number == "2"
            assert carried[draft.pk].number is None
            for before in (superseded, current):
                after = carried[before.pk]
                assert (
                    after.markdown,
                    after.html,
                    after.status,
                    after.published_at,
                    after.publisher_subject,
                ) == (
                    before.markdown,
                    before.html,
                    before.status,
                    before.published_at,
                    before.publisher_subject,
                )
            assert carried[draft.pk].markdown == draft.markdown
        finally:
            # Leave the database at the latest migration for whatever runs next.
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
