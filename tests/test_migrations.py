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
