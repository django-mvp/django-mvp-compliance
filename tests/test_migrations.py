"""No shipped migration writes to a published version or a recorded acceptance.

``VersionManager.use_in_migrations`` and ``AcceptanceManager.use_in_migrations``
close every bulk route a migration could take, but a historical model has no
custom ``save()`` — so a data migration that called ``save()`` directly on one
would still slip past. This asserts the residue stays closed the only other
way it can be: no shipped migration performs a data write at all
(docs/adr/0004-migrations-are-the-one-route-immutability-cannot-close.md).
"""

import importlib
import pkgutil

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations.special import RunPython, RunSQL
from django.utils import timezone

import mvp_compliance.migrations as migrations_package
from tests.factories import UserFactory, VersionFactory


class TestMigrationOperations:
    def test_no_shipped_migration_uses_runpython_or_runsql(self):
        # A data migration that is ever needed goes through the historical model's
        # own manager and publish()/save()/record(), never raw SQL (docs/adr/0004).
        for module_info in pkgutil.iter_modules(migrations_package.__path__):
            module = importlib.import_module(
                f"{migrations_package.__name__}.{module_info.name}"
            )
            migration = module.Migration
            for operation in migration.operations:
                assert not isinstance(operation, (RunPython, RunSQL)), (
                    f"{module_info.name} contains a "
                    f"{type(operation).__name__} operation — see docs/adr/0004 first"
                )

    @pytest.mark.django_db
    def test_the_models_need_no_new_migration(self):
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)


@pytest.mark.django_db
class TestHistoricalAcceptance:
    def test_a_migration_can_bulk_create_acceptances(self):
        # The historical manager carries the current queryset (use_in_migrations),
        # and its bulk_create() must not apply a guard written for the real model.
        loader = MigrationLoader(connection)
        (leaf,) = loader.graph.leaf_nodes(app="mvp_compliance")
        Acceptance = loader.project_state(leaf).apps.get_model(
            "mvp_compliance", "Acceptance"
        )
        user = UserFactory()
        version = VersionFactory()
        version.publish()

        Acceptance.objects.bulk_create(
            [
                Acceptance(
                    user_id=user.pk,
                    subject=str(user.pk),
                    version_id=version.pk,
                    accepted_at=timezone.now(),
                )
            ]
        )

        assert Acceptance.objects.filter(version_id=version.pk).count() == 1


@pytest.mark.django_db(transaction=True)
class TestEnforcedColumn:
    """FR-024: a document that existed before the column is enforced, and nothing else moves.

    SQLite's schema editor will not run inside a transaction, so the class runs
    outside one and puts the database back at the latest migration afterwards.
    """

    first = [("mvp_compliance", "0001_initial")]

    @pytest.fixture
    def executor(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.first)
        yield executor
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_a_document_that_existed_before_the_column_is_enforced_and_its_record_is_unchanged(
        self, executor
    ):
        before = executor.loader.project_state(self.first).apps
        document = before.get_model("mvp_compliance", "Document").objects.create(
            name="Terms", slug="terms"
        )
        version = before.get_model("mvp_compliance", "Version").objects.create(
            document=document,
            number="2026.1",
            markdown="Wording",
            html="<p>Wording</p>",
            status="current",
            published_at=timezone.now(),
        )
        person = UserFactory()
        before.get_model("mvp_compliance", "Acceptance").objects.create(
            user_id=person.pk,
            subject=str(person.pk),
            version=version,
            accepted_at=timezone.now(),
        )
        held = {
            name: list(before.get_model("mvp_compliance", name).objects.values())
            for name in ("Version", "Acceptance")
        }

        executor = MigrationExecutor(connection)
        targets = [("mvp_compliance", "0002_document_enforced")]
        executor.migrate(targets)

        after = executor.loader.project_state(targets).apps
        assert after.get_model("mvp_compliance", "Document").objects.get().enforced
        for name, rows in held.items():
            assert (
                list(after.get_model("mvp_compliance", name).objects.values()) == rows
            )


@pytest.mark.django_db(transaction=True)
class TestSummaryColumn:
    """A published version that existed before the summary column has none, and
    nothing else about it or its acceptance moves (Article XV).

    Runs outside a transaction for the reason ``TestEnforcedColumn`` gives.
    """

    before_summary = [("mvp_compliance", "0002_document_enforced")]

    @pytest.fixture
    def executor(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before_summary)
        yield executor
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_a_published_version_gains_an_empty_summary_and_is_otherwise_unchanged(
        self, executor
    ):
        before = executor.loader.project_state(self.before_summary).apps
        document = before.get_model("mvp_compliance", "Document").objects.create(
            name="Terms", slug="terms"
        )
        version = before.get_model("mvp_compliance", "Version").objects.create(
            document=document,
            number="2026.1",
            markdown="Wording",
            html="<p>Wording</p>",
            status="current",
            published_at=timezone.now(),
        )
        person = UserFactory()
        before.get_model("mvp_compliance", "Acceptance").objects.create(
            user_id=person.pk,
            subject=str(person.pk),
            version=version,
            accepted_at=timezone.now(),
        )
        held = {
            name: list(before.get_model("mvp_compliance", name).objects.values())
            for name in ("Version", "Acceptance")
        }

        executor = MigrationExecutor(connection)
        targets = [("mvp_compliance", "0003_version_summary")]
        executor.migrate(targets)

        after = executor.loader.project_state(targets).apps
        (migrated,) = after.get_model("mvp_compliance", "Version").objects.values()
        assert migrated == {**held["Version"][0], "summary": ""}
        assert (
            list(after.get_model("mvp_compliance", "Acceptance").objects.values())
            == held["Acceptance"]
        )
