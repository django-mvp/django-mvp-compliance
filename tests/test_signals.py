"""The signals sent for a version locked, returned or published and a translation put live or returned (FS-015)."""

import pytest
from django.contrib import admin
from django.db import transaction
from django.urls import path, reverse

from mvp_compliance.exceptions import PublishError
from mvp_compliance.models import Translation, Version
from mvp_compliance.signals import (
    translation_published,
    translation_returned_to_draft,
    version_pending,
    version_published,
    version_returned_to_draft,
)
from tests.conftest import grant
from tests.factories import TranslationFactory, UserFactory, VersionFactory

urlpatterns = [path("admin/", admin.site.urls)]


@pytest.fixture
def listen():
    """Connect a recorder to any signal, and return the list it fills."""
    connected = []

    def listen_to(signal):
        calls: list[dict] = []

        def record(sender, **kwargs):
            calls.append({"sender": sender, **kwargs})

        signal.connect(record, weak=False)
        connected.append((signal, record))
        return calls

    yield listen_to
    for signal, receiver in connected:
        signal.disconnect(receiver)


@pytest.fixture
def pending(db):
    return VersionFactory(pending=True)


@pytest.fixture
def translation_publisher(db):
    """Somebody who may put a translation live, and nothing on versions."""
    return grant(
        UserFactory(is_staff=True),
        "add_translation",
        "change_translation",
        "view_translation",
        "view_version",
        "publish_translation",
    )


@pytest.mark.django_db
class TestVersionPending:
    def test_locking_sends_once_after_commit_with_the_version_and_who_locked(
        self, listen, django_capture_on_commit_callbacks, draft, user
    ):
        calls = listen(version_pending)

        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            draft.lock_for_translation(by=user)
        assert calls == []
        for callback in callbacks:
            callback()

        assert len(calls) == 1
        assert calls[0]["sender"] is Version
        assert calls[0]["version"] == draft
        assert calls[0]["by"] == user

    def test_locking_with_nobody_named_passes_none(
        self, listen, django_capture_on_commit_callbacks, draft
    ):
        calls = listen(version_pending)

        with django_capture_on_commit_callbacks(execute=True):
            draft.lock_for_translation()

        assert calls[0]["by"] is None

    def test_the_receiver_sees_the_version_pending(
        self, listen, django_capture_on_commit_callbacks, draft
    ):
        seen = []

        def look(sender, version, **kwargs):
            seen.append(Version.objects.get(pk=version.pk).status)

        version_pending.connect(look, weak=False)
        try:
            with django_capture_on_commit_callbacks(execute=True):
                draft.lock_for_translation()
        finally:
            version_pending.disconnect(look)

        assert seen == [Version.Status.PENDING]

    def test_a_refused_lock_sends_nothing(
        self, listen, django_capture_on_commit_callbacks, published_version
    ):
        calls = listen(version_pending)
        empty = VersionFactory(markdown="   \n\n   ")

        with django_capture_on_commit_callbacks(execute=True):
            with pytest.raises(PublishError):
                published_version.lock_for_translation()
            with pytest.raises(PublishError):
                empty.lock_for_translation()

        assert calls == []

    def test_a_lock_inside_a_rolled_back_block_sends_nothing(
        self, listen, django_capture_on_commit_callbacks, draft
    ):
        calls = listen(version_pending)

        with (
            django_capture_on_commit_callbacks(execute=True),
            pytest.raises(RuntimeError),
            transaction.atomic(),
        ):
            draft.lock_for_translation()
            raise RuntimeError("roll back")

        assert calls == []

    def test_a_raising_receiver_leaves_the_lock_and_the_next_receiver_runs(
        self, listen, django_capture_on_commit_callbacks, draft
    ):
        def fail(sender, **kwargs):
            raise RuntimeError("receiver failed")

        version_pending.connect(fail, weak=False)
        try:
            calls = listen(version_pending)
            with django_capture_on_commit_callbacks(execute=True):
                draft.lock_for_translation()
        finally:
            version_pending.disconnect(fail)

        draft.refresh_from_db()
        assert draft.status == Version.Status.PENDING
        assert len(calls) == 1


@pytest.mark.django_db
class TestVersionReturnedToDraft:
    def test_returning_sends_once_after_commit_with_the_version_and_who_returned(
        self, listen, django_capture_on_commit_callbacks, pending, user
    ):
        calls = listen(version_returned_to_draft)

        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            pending.return_to_draft(by=user)
        assert calls == []
        for callback in callbacks:
            callback()

        assert len(calls) == 1
        assert calls[0]["sender"] is Version
        assert calls[0]["version"] == pending
        assert calls[0]["by"] == user

    def test_returning_with_nobody_named_passes_none(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        calls = listen(version_returned_to_draft)

        with django_capture_on_commit_callbacks(execute=True):
            pending.return_to_draft()

        assert calls[0]["by"] is None

    def test_a_refused_return_sends_nothing(
        self, listen, django_capture_on_commit_callbacks, draft
    ):
        calls = listen(version_returned_to_draft)

        with (
            django_capture_on_commit_callbacks(execute=True),
            pytest.raises(PublishError),
        ):
            draft.return_to_draft()

        assert calls == []

    def test_a_return_inside_a_rolled_back_block_sends_nothing(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        calls = listen(version_returned_to_draft)

        with (
            django_capture_on_commit_callbacks(execute=True),
            pytest.raises(RuntimeError),
            transaction.atomic(),
        ):
            pending.return_to_draft()
            raise RuntimeError("roll back")

        assert calls == []

    def test_a_raising_receiver_leaves_the_return_and_the_next_receiver_runs(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        def fail(sender, **kwargs):
            raise RuntimeError("receiver failed")

        version_returned_to_draft.connect(fail, weak=False)
        try:
            calls = listen(version_returned_to_draft)
            with django_capture_on_commit_callbacks(execute=True):
                pending.return_to_draft()
        finally:
            version_returned_to_draft.disconnect(fail)

        pending.refresh_from_db()
        assert pending.status == Version.Status.DRAFT
        assert len(calls) == 1


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestTranslationPublished:
    def test_putting_live_sends_once_after_commit_with_the_translation_and_publisher(
        self, listen, django_capture_on_commit_callbacks, pending, user
    ):
        translation = TranslationFactory(version=pending)
        calls = listen(translation_published)

        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            translation.publish(publisher=user)
        assert calls == []
        for callback in callbacks:
            callback()

        assert len(calls) == 1
        assert calls[0]["sender"] is Translation
        assert calls[0]["translation"] == translation
        assert calls[0]["publisher"] == user
        assert calls[0]["replaced"] is None

    def test_putting_live_with_nobody_named_passes_none(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        translation = TranslationFactory(version=pending)
        calls = listen(translation_published)

        with django_capture_on_commit_callbacks(execute=True):
            translation.publish()

        assert calls[0]["publisher"] is None

    def test_a_correction_reports_the_wording_it_replaced_already_superseded(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        first = TranslationFactory(version=pending, markdown="Erster Text")
        first.publish()
        correction = TranslationFactory(version=pending, markdown="Besserer Text")
        calls = listen(translation_published)

        with django_capture_on_commit_callbacks(execute=True):
            correction.publish()

        assert len(calls) == 1
        replaced = calls[0]["replaced"]
        assert replaced == first
        assert replaced.status == Translation.Status.SUPERSEDED
        assert Translation.objects.get(pk=first.pk).status == (
            Translation.Status.SUPERSEDED
        )

    def test_the_receiver_sees_the_translation_current(
        self, django_capture_on_commit_callbacks, pending
    ):
        translation = TranslationFactory(version=pending)
        seen = []

        def look(sender, translation, **kwargs):
            seen.append(Translation.objects.get(pk=translation.pk).status)

        translation_published.connect(look, weak=False)
        try:
            with django_capture_on_commit_callbacks(execute=True):
                translation.publish()
        finally:
            translation_published.disconnect(look)

        assert seen == [Translation.Status.CURRENT]

    def test_a_refused_publication_sends_nothing(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        live = TranslationFactory(version=pending)
        live.publish()
        same_wording = TranslationFactory(version=pending, markdown=live.markdown)
        empty = TranslationFactory(version=pending, language="fr", markdown="   ")
        calls = listen(translation_published)

        with django_capture_on_commit_callbacks(execute=True):
            with pytest.raises(PublishError):
                live.publish()
            with pytest.raises(PublishError):
                same_wording.publish()
            with pytest.raises(PublishError):
                empty.publish()

        assert calls == []

    def test_a_publication_inside_a_rolled_back_block_sends_nothing(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        translation = TranslationFactory(version=pending)
        calls = listen(translation_published)

        with (
            django_capture_on_commit_callbacks(execute=True),
            pytest.raises(RuntimeError),
            transaction.atomic(),
        ):
            translation.publish()
            raise RuntimeError("roll back")

        assert calls == []

    def test_a_raising_receiver_leaves_it_live_and_the_next_receiver_runs(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        translation = TranslationFactory(version=pending)

        def fail(sender, **kwargs):
            raise RuntimeError("receiver failed")

        translation_published.connect(fail, weak=False)
        try:
            calls = listen(translation_published)
            with django_capture_on_commit_callbacks(execute=True):
                translation.publish()
        finally:
            translation_published.disconnect(fail)

        translation.refresh_from_db()
        assert translation.status == Translation.Status.CURRENT
        assert len(calls) == 1


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestTranslationReturnedToDraft:
    def test_returning_sends_once_for_each_translation_it_returns(
        self, listen, django_capture_on_commit_callbacks, pending, user
    ):
        german = TranslationFactory(version=pending, language="de")
        french = TranslationFactory(version=pending, language="fr")
        german.publish()
        french.publish()
        calls = listen(translation_returned_to_draft)

        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            pending.return_to_draft(by=user)
        assert calls == []
        for callback in callbacks:
            callback()

        assert {call["translation"] for call in calls} == {german, french}
        assert len(calls) == 2
        for call in calls:
            assert call["sender"] is Translation
            assert call["by"] == user
            assert call["translation"].status == Translation.Status.DRAFT

    def test_a_translation_already_a_draft_is_not_announced(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        live = TranslationFactory(version=pending, language="de")
        live.publish()
        TranslationFactory(version=pending, language="fr")
        calls = listen(translation_returned_to_draft)

        with django_capture_on_commit_callbacks(execute=True):
            pending.return_to_draft()

        assert [call["translation"] for call in calls] == [live]
        assert calls[0]["by"] is None

    def test_a_version_with_no_live_translation_announces_none(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        calls = listen(translation_returned_to_draft)

        with django_capture_on_commit_callbacks(execute=True):
            pending.return_to_draft()

        assert calls == []

    def test_a_refused_or_rolled_back_return_sends_nothing(
        self, listen, django_capture_on_commit_callbacks, pending, draft
    ):
        TranslationFactory(version=pending).publish()
        calls = listen(translation_returned_to_draft)

        with django_capture_on_commit_callbacks(execute=True):
            with pytest.raises(PublishError):
                draft.return_to_draft()
            with pytest.raises(RuntimeError), transaction.atomic():
                pending.return_to_draft()
                raise RuntimeError("roll back")

        assert calls == []

    def test_a_raising_receiver_leaves_the_return_and_the_next_receiver_runs(
        self, listen, django_capture_on_commit_callbacks, pending
    ):
        translation = TranslationFactory(version=pending)
        translation.publish()

        def fail(sender, **kwargs):
            raise RuntimeError("receiver failed")

        translation_returned_to_draft.connect(fail, weak=False)
        try:
            calls = listen(translation_returned_to_draft)
            with django_capture_on_commit_callbacks(execute=True):
                pending.return_to_draft()
        finally:
            translation_returned_to_draft.disconnect(fail)

        translation.refresh_from_db()
        assert translation.status == Translation.Status.DRAFT
        assert len(calls) == 1


@pytest.mark.django_db
@pytest.mark.urls(__name__)
@pytest.mark.usefixtures("site_languages")
class TestSignalsFromTheAdmin:
    def test_the_lock_page_sends_version_pending_naming_the_caller(
        self, client, listen, django_capture_on_commit_callbacks, publisher, draft
    ):
        client.force_login(publisher)
        calls = listen(version_pending)

        with django_capture_on_commit_callbacks(execute=True):
            client.post(reverse("admin:mvp_compliance_version_lock", args=[draft.pk]))

        assert len(calls) == 1
        assert calls[0]["version"] == draft
        assert calls[0]["by"] == publisher

    def test_the_return_page_sends_both_signals_naming_the_caller(
        self, client, listen, django_capture_on_commit_callbacks, publisher, pending
    ):
        translation = TranslationFactory(version=pending)
        translation.publish()
        client.force_login(publisher)
        returned = listen(version_returned_to_draft)
        translations = listen(translation_returned_to_draft)

        with django_capture_on_commit_callbacks(execute=True):
            client.post(
                reverse(
                    "admin:mvp_compliance_version_return_to_draft", args=[pending.pk]
                )
            )

        assert [call["by"] for call in returned] == [publisher]
        assert [call["translation"] for call in translations] == [translation]
        assert translations[0]["by"] == publisher

    def test_the_publish_page_sends_version_published(
        self, client, listen, django_capture_on_commit_callbacks, publisher, pending
    ):
        client.force_login(publisher)
        calls = listen(version_published)

        with django_capture_on_commit_callbacks(execute=True):
            client.post(
                reverse("admin:mvp_compliance_version_publish", args=[pending.pk])
            )

        assert [call["publisher"] for call in calls] == [publisher]

    def test_the_put_live_page_sends_translation_published_naming_the_caller(
        self,
        client,
        listen,
        django_capture_on_commit_callbacks,
        translation_publisher,
        pending,
    ):
        translation = TranslationFactory(version=pending)
        client.force_login(translation_publisher)
        calls = listen(translation_published)

        with django_capture_on_commit_callbacks(execute=True):
            client.post(
                reverse(
                    "admin:mvp_compliance_translation_publish", args=[translation.pk]
                )
            )

        assert len(calls) == 1
        assert calls[0]["translation"] == translation
        assert calls[0]["publisher"] == translation_publisher

    def test_a_refused_change_from_the_admin_sends_nothing(
        self, client, listen, django_capture_on_commit_callbacks, publisher, pending
    ):
        client.force_login(publisher)
        calls = listen(version_pending)

        with django_capture_on_commit_callbacks(execute=True):
            client.post(reverse("admin:mvp_compliance_version_lock", args=[pending.pk]))

        assert calls == []


@pytest.mark.django_db
@pytest.mark.usefixtures("site_languages")
class TestAReceiverTranslatingFromCode:
    def test_a_translation_added_by_a_version_pending_receiver_goes_live_with_the_version(
        self, django_capture_on_commit_callbacks, draft
    ):
        # The receiver in docs/authoring.md "From code".
        def translate(sender, version, by, **kwargs):
            translation = Translation.objects.create(
                version=version, language="de", markdown="Hallo Welt"
            )
            translation.publish()

        version_pending.connect(translate, weak=False)
        try:
            with django_capture_on_commit_callbacks(execute=True):
                draft.lock_for_translation()
        finally:
            version_pending.disconnect(translate)

        german = Translation.objects.get(version=draft, language="de")
        assert german.status == Translation.Status.CURRENT
        assert list(Translation.objects.live()) == []

        draft.publish()

        assert list(Translation.objects.live()) == [german]
