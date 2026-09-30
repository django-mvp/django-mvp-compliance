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
from django.db.migrations.operations.special import RunPython, RunSQL
from django.utils import timezone

import mvp_compliance.migrations as migrations_package
from tests.factories import UserFactory


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


@pytest.mark.django_db(transaction=True)
class TestPublisherMigration:
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
class TestDocumentKindMigration:
    def test_documents_versions_and_acceptances_are_carried_and_every_document_is_agreed(
        self,
    ):
        before = [("mvp_compliance", "0007_document_slug")]
        after = [("mvp_compliance", "0008_document_kind")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        old_apps = executor.loader.project_state(before).apps
        published_at = timezone.now()
        accepted_at = timezone.now()
        user = UserFactory()
        document = old_apps.get_model("mvp_compliance", "Document").objects.create(
            name="Terms", slug="terms"
        )
        other = old_apps.get_model("mvp_compliance", "Document").objects.create(
            name="Privacy", slug="privacy"
        )
        version = old_apps.get_model("mvp_compliance", "Version").objects.create(
            document=document,
            number="2026.1",
            markdown="Wording",
            html="<p>Wording</p>",
            status="current",
            published_at=published_at,
        )
        acceptance = old_apps.get_model("mvp_compliance", "Acceptance").objects.create(
            user_id=user.pk,
            subject=str(user.pk),
            version=version,
            accepted_at=accepted_at,
        )

        try:
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            new_apps = executor.loader.project_state(after).apps
            documents = new_apps.get_model("mvp_compliance", "Document").objects
            carried_version = new_apps.get_model(
                "mvp_compliance", "Version"
            ).objects.get(pk=version.pk)
            carried_acceptance = new_apps.get_model(
                "mvp_compliance", "Acceptance"
            ).objects.get(pk=acceptance.pk)

            assert {(d.name, d.slug, d.kind) for d in documents.all()} == {
                ("Terms", "terms", "agreed"),
                ("Privacy", "privacy", "agreed"),
            }
            assert documents.get(pk=other.pk).kind == "agreed"
            assert carried_version.document_id == document.pk
            assert carried_version.number == "2026.1"
            assert carried_version.markdown == "Wording"
            assert carried_version.html == "<p>Wording</p>"
            assert carried_version.status == "current"
            assert carried_version.published_at == published_at
            assert carried_acceptance.version_id == version.pk
            assert carried_acceptance.subject == str(user.pk)
            assert carried_acceptance.accepted_at == accepted_at
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())

    def test_a_migration_before_the_kind_can_still_bulk_create_acceptances(self):
        # The historical manager carries the current queryset (use_in_migrations),
        # so its bulk_create() must not ask about a column that state lacks.
        before = [("mvp_compliance", "0007_document_slug")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        old_apps = executor.loader.project_state(before).apps
        user = UserFactory()
        document = old_apps.get_model("mvp_compliance", "Document").objects.create(
            name="Terms", slug="terms"
        )
        version = old_apps.get_model("mvp_compliance", "Version").objects.create(
            document=document,
            number="2026.1",
            markdown="Wording",
            html="<p>Wording</p>",
            status="current",
            published_at=timezone.now(),
        )
        Acceptance = old_apps.get_model("mvp_compliance", "Acceptance")

        try:
            Acceptance.objects.bulk_create(
                [
                    Acceptance(
                        user_id=user.pk,
                        subject=str(user.pk),
                        version=version,
                        accepted_at=timezone.now(),
                    )
                ]
            )

            assert Acceptance.objects.filter(version=version).count() == 1
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
