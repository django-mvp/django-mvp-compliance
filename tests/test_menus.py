"""Tests for mvp_compliance.menus."""

import pytest
from django.urls import reverse
from mvp.menus import AccountCenterMenu


def agreed_entries(request):
    """The processed account-area entries that lead to the list of agreed documents."""
    return [
        child
        for child in AccountCenterMenu.process(request).children
        if child.name == "agreed-documents"
    ]


@pytest.mark.django_db
class TestAccountAreaEntry:
    """US-1 scenario 10, SC-004: the list is reached from the account area's own menu."""

    def test_a_signed_in_request_finds_an_entry_to_the_list_in_the_account_menu(
        self, rf, user
    ):
        request = rf.get(reverse("account-center"))
        request.user = user

        entries = agreed_entries(request)

        assert [entry.url for entry in entries] == [reverse("mvp_compliance:agreed")]

    def test_on_the_list_the_entry_is_selected_and_the_page_is_drawn_with_the_account_menu(
        self, client, user
    ):
        client.force_login(user)

        response = client.get(reverse("mvp_compliance:agreed"))

        entries = agreed_entries(response.wsgi_request)
        assert [entry.selected for entry in entries] == [True]
        assert response.context["mounted_menu"].name == AccountCenterMenu.name


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_mvp_only")
class TestWithoutThePackagePages:
    """US-3 scenario 3: a project that mounts only django-mvp's pages gets no entry
    for the list and no failure."""

    def test_the_account_menu_has_no_entry_for_the_list(self, rf, user):
        request = rf.get("/account/")
        request.user = user

        assert agreed_entries(request) == []

    def test_the_account_areas_landing_page_answers(self, client, user):
        client.force_login(user)

        response = client.get(reverse("account-center"))

        assert response.status_code == 200
