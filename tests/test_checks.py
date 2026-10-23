"""Tests for mvp_compliance.checks."""

from unittest.mock import patch

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.core.checks import run_checks
from django.test import override_settings

AGREEMENT = "mvp_compliance.middleware.AgreementMiddleware"
AUTHENTICATION = "django.contrib.auth.middleware.AuthenticationMiddleware"
SESSIONS = "django.contrib.sessions.middleware.SessionMiddleware"
OURS = {"mvp_compliance.E001", "mvp_compliance.E002"}


class SiteAuthenticationMiddleware(AuthenticationMiddleware):
    """A project's own subclass, which identifies the signed-in user all the same."""


def reported(*middleware):
    """The ids of this package's checks that fire with ``middleware`` listed."""
    with override_settings(MIDDLEWARE=list(middleware)):
        return {message.id for message in run_checks()} & OURS


class TestAgreementChecks:
    def test_a_project_that_configured_the_check_correctly_is_told_nothing(self):
        assert reported(SESSIONS, AUTHENTICATION, AGREEMENT) == set()

    @pytest.mark.urls("tests.urls_mvp_only")
    def test_pages_of_the_package_that_are_not_mounted_are_an_error(self):
        assert reported(SESSIONS, AUTHENTICATION, AGREEMENT) == {"mvp_compliance.E001"}

    def test_the_check_listed_ahead_of_authentication_is_an_error(self):
        assert reported(SESSIONS, AGREEMENT, AUTHENTICATION) == {"mvp_compliance.E002"}

    def test_the_check_with_no_authentication_middleware_at_all_is_an_error(self):
        assert reported(SESSIONS, AGREEMENT) == {"mvp_compliance.E002"}

    def test_a_subclass_of_the_authentication_middleware_ahead_of_it_is_enough(self):
        subclass = f"{__name__}.SiteAuthenticationMiddleware"

        assert reported(SESSIONS, subclass, AGREEMENT) == set()

    @pytest.mark.urls("tests.urls_mvp_only")
    def test_nothing_is_reported_while_the_middleware_is_not_listed(self):
        assert reported(SESSIONS) == set()


class TestListSettingChecks:
    @pytest.mark.parametrize(
        "setting",
        [
            "MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS",
            "MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS",
        ],
    )
    def test_a_list_setting_given_as_a_string_is_an_error(self, setting):
        with override_settings(
            MIDDLEWARE=[SESSIONS, AUTHENTICATION, AGREEMENT], **{setting: "/help/"}
        ):
            ids = {message.id for message in run_checks()}

        assert "mvp_compliance.E003" in ids

    @pytest.mark.parametrize(
        "setting",
        [
            "MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS",
            "MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS",
        ],
    )
    def test_a_list_setting_given_as_a_list_is_told_nothing(self, setting):
        with override_settings(
            MIDDLEWARE=[SESSIONS, AUTHENTICATION, AGREEMENT], **{setting: ["/help/"]}
        ):
            ids = {message.id for message in run_checks()}

        assert "mvp_compliance.E003" not in ids

    @pytest.mark.parametrize("interval", ["60", None, True])
    def test_an_interval_that_is_not_a_number_is_an_error(self, interval):
        with override_settings(
            MIDDLEWARE=[SESSIONS, AUTHENTICATION, AGREEMENT],
            MVP_COMPLIANCE_AGREEMENT_CHECK_INTERVAL=interval,
        ):
            ids = {message.id for message in run_checks()}

        assert "mvp_compliance.E004" in ids

    @pytest.mark.parametrize("interval", [0, 5, 2.5])
    def test_an_interval_that_is_a_number_is_not_reported(self, interval):
        with override_settings(
            MIDDLEWARE=[SESSIONS, AUTHENTICATION, AGREEMENT],
            MVP_COMPLIANCE_AGREEMENT_CHECK_INTERVAL=interval,
        ):
            ids = {message.id for message in run_checks()}

        assert "mvp_compliance.E004" not in ids


PERSONAL_DATA = {
    "mvp_compliance.E005",
    "mvp_compliance.E006",
    "mvp_compliance.E007",
    "mvp_compliance.E008",
}
NOTES = "tests.kinds.Notes"
ACCOUNT_MIDDLEWARE = "allauth.account.middleware.AccountMiddleware"


def personal_data_messages(**overrides):
    """This check's messages, with the given settings overridden."""
    with override_settings(**overrides):
        return [message for message in run_checks() if message.id in PERSONAL_DATA]


def declared(*paths, **overrides):
    """This check's messages when the project declares ``paths``."""
    return personal_data_messages(MVP_COMPLIANCE_PERSONAL_DATA=list(paths), **overrides)


class TestPersonalDataCheck:
    def test_a_project_that_declares_nothing_is_told_nothing(self):
        assert personal_data_messages() == []

    def test_an_empty_declaration_is_told_nothing(self):
        assert declared() == []

    def test_a_valid_declaration_is_told_nothing(self):
        assert declared(NOTES, "tests.kinds.Custom") == []

    def test_a_tuple_is_as_good_as_a_list(self):
        messages = personal_data_messages(MVP_COMPLIANCE_PERSONAL_DATA=(NOTES,))

        assert messages == []

    def test_a_string_instead_of_a_list_is_one_error(self):
        messages = personal_data_messages(MVP_COMPLIANCE_PERSONAL_DATA=NOTES)

        assert [message.id for message in messages] == ["mvp_compliance.E005"]

    def test_a_path_that_cannot_be_imported_is_an_error_naming_it(self):
        messages = declared("tests.kinds.Nothing")

        assert [message.id for message in messages] == ["mvp_compliance.E006"]
        assert "tests.kinds.Nothing" in messages[0].msg

    def test_a_class_that_is_not_a_kind_is_an_error_naming_it(self):
        messages = declared("tests.kinds.NotAKind")

        assert [message.id for message in messages] == ["mvp_compliance.E006"]
        assert "tests.kinds.NotAKind" in messages[0].msg

    def test_an_entry_that_is_not_a_string_is_an_error(self):
        messages = declared(42)

        assert [message.id for message in messages] == ["mvp_compliance.E006"]

    def test_each_bad_path_is_its_own_error(self):
        messages = declared("tests.kinds.Nothing", NOTES, "tests.kinds.NotAKind")

        assert [message.id for message in messages] == ["mvp_compliance.E006"] * 2

    def test_a_field_the_model_lacks_is_an_error_naming_the_kind(self):
        messages = declared("tests.kinds.MissingField")

        assert [message.id for message in messages] == ["mvp_compliance.E007"]
        assert "tests.kinds.MissingField" in messages[0].msg

    def test_two_kinds_with_the_same_key_are_an_error_naming_both(self):
        messages = declared(NOTES, "tests.other_kinds.Notes")

        assert [message.id for message in messages] == ["mvp_compliance.E006"]
        assert NOTES in messages[0].msg
        assert "tests.other_kinds.Notes" in messages[0].msg

    def test_allauth_not_installed_is_an_error(self):
        installed = apps.is_installed

        with patch.object(
            apps,
            "is_installed",
            side_effect=lambda name: name != "allauth.account" and installed(name),
        ):
            messages = declared(NOTES)

        assert [message.id for message in messages] == ["mvp_compliance.E008"]

    def test_the_account_middleware_missing_is_an_error(self):
        middleware = [
            name for name in settings.MIDDLEWARE if name != ACCOUNT_MIDDLEWARE
        ]

        messages = declared(NOTES, MIDDLEWARE=middleware)

        assert [message.id for message in messages] == ["mvp_compliance.E008"]

    def test_allauth_is_not_asked_for_while_nothing_is_declared(self):
        middleware = [
            name for name in settings.MIDDLEWARE if name != ACCOUNT_MIDDLEWARE
        ]

        assert personal_data_messages(MIDDLEWARE=middleware) == []
