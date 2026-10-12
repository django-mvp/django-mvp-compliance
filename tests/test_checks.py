"""Tests for mvp_compliance.checks."""

import pytest
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
    @pytest.mark.parametrize("setting", ["MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS"])
    def test_a_list_setting_given_as_a_string_is_an_error(self, setting):
        with override_settings(
            MIDDLEWARE=[SESSIONS, AUTHENTICATION, AGREEMENT], **{setting: "/help/"}
        ):
            ids = {message.id for message in run_checks()}

        assert "mvp_compliance.E003" in ids

    @pytest.mark.parametrize("setting", ["MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS"])
    def test_a_list_setting_given_as_a_list_is_told_nothing(self, setting):
        with override_settings(
            MIDDLEWARE=[SESSIONS, AUTHENTICATION, AGREEMENT], **{setting: ["/help/"]}
        ):
            ids = {message.id for message in run_checks()}

        assert "mvp_compliance.E003" not in ids
