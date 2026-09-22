"""No shipped migration writes to a published version or a recorded acceptance (D10).

``VersionManager.use_in_migrations`` and ``AcceptanceManager.use_in_migrations``
close every bulk route a migration could take, but a historical model has no
custom ``save()`` — so a data migration that called ``save()`` directly on one
would still slip past. This asserts the residue stays closed the only other
way it can be: no shipped migration performs a data write at all.
"""

import importlib
import pkgutil

from django.db.migrations.operations.special import RunPython, RunSQL

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
