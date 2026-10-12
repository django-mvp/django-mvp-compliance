"""Tests for mvp_compliance.middleware.

The module is its own URLconf (``@pytest.mark.urls(__name__)``): it mounts the
package, django-mvp and the admin, and routes the few plain addresses the check
is asked about. A view that records being called is how a request that was
stopped is told from one that was served.
"""

from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse
from django.test import Client, modify_settings
from django.test.utils import CaptureQueriesContext
from django.urls import get_script_prefix, include, path, reverse
from django.utils import timezone

from mvp_compliance.models import Acceptance, Document
from tests.factories import DocumentFactory, UserFactory, VersionFactory

MIDDLEWARE = "mvp_compliance.middleware.AgreementMiddleware"

#: The addresses of the views that were called, in order.
called: list[str] = []


def recording_view(request, **kwargs):
    called.append(request.path)
    return HttpResponse("served")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("legal/", include("mvp_compliance.urls")),
    path("", include("mvp.urls")),
    path("elsewhere/", recording_view, name="elsewhere"),
    path("private/", login_required(recording_view), name="private"),
    path("signout/", recording_view, name="logout"),
    path("static/<path:name>", recording_view),
    path("staticfiles/<path:name>", recording_view),
    path("assets/<path:name>", recording_view),
    path("uploads/<path:name>", recording_view),
]

pytestmark = pytest.mark.urls(__name__)


@pytest.fixture(autouse=True)
def no_calls():
    called.clear()


@pytest.fixture
def check_on():
    with modify_settings(MIDDLEWARE={"append": MIDDLEWARE}):
        yield


@pytest.fixture
def media_url_is_unset(settings):
    # Django returns an unset MEDIA_URL as the site root.
    assert get_script_prefix() == settings.MEDIA_URL


@pytest.fixture
def version(db):
    """The version in force of an enforced document nobody has accepted."""
    version = VersionFactory(document=DocumentFactory())
    version.publish()
    return version


@pytest.fixture
def stopped(client, version):
    """A signed-in user who has not accepted ``version``."""
    user = UserFactory()
    client.force_login(user)
    return user


def agreement_address():
    return reverse("mvp_compliance:agree")


def sent_to_the_page_that_asks(response):
    return (
        response.status_code in (302, 303)
        and urlsplit(response["Location"]).path == agreement_address()
    )


def return_address(location):
    """The ``next`` value a redirect to the page that asks carries."""
    return parse_qs(urlsplit(location).query)["next"]


def without_the_check(method, address, **extra):
    """Answer a request made by a new client when the check is not installed."""
    with modify_settings(MIDDLEWARE={"remove": MIDDLEWARE}):
        return getattr(Client(), method)(address, **extra)


def remember_finding(client):
    """Make a request the check finds clear, and return the session key it wrote."""
    before = dict(client.session)
    response = client.get("/elsewhere/")
    assert response.status_code == 200
    (key,) = dict(client.session).keys() - before.keys()
    return key


def after(seconds):
    return patch(
        "django.utils.timezone.now",
        return_value=timezone.now() + timedelta(seconds=seconds),
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("check_on", "media_url_is_unset")
class TestAgreementCheck:
    def test_a_stopped_user_is_sent_to_the_page_that_asks_with_the_address_wanted(
        self, client, stopped
    ):
        response = client.get("/elsewhere/?tab=2&sort=name")

        assert sent_to_the_page_that_asks(response)
        assert return_address(response["Location"]) == ["/elsewhere/?tab=2&sort=name"]
        assert called == []

    def test_an_unset_media_url_covers_nothing(self, client, stopped):
        response = client.get("/elsewhere/")

        assert sent_to_the_page_that_asks(response)

    def test_the_address_wanted_is_served_once_the_acceptance_is_recorded(
        self, client, stopped, version
    ):
        assert sent_to_the_page_that_asks(client.get("/elsewhere/"))

        Acceptance.objects.record(stopped, version)
        response = client.get("/elsewhere/")

        assert response.status_code == 200
        assert called == ["/elsewhere/"]

    def test_a_user_who_accepted_every_enforced_document_is_served(
        self, client, stopped, version
    ):
        Acceptance.objects.record(stopped, version)

        response = client.get("/elsewhere/")

        assert response.status_code == 200

    def test_a_user_whose_only_outstanding_document_is_not_enforced_is_served(
        self, client, db
    ):
        unenforced = VersionFactory(document=DocumentFactory(enforced=False))
        unenforced.publish()
        user = UserFactory()
        client.force_login(user)
        assert Document.objects.outstanding_for(user).exists()

        response = client.get("/elsewhere/")

        assert response.status_code == 200

    @pytest.mark.parametrize(
        ("address", "status"), [("/elsewhere/", 200), ("/private/", 302)]
    )
    def test_a_visitor_who_is_not_signed_in_is_answered_as_without_the_check(
        self, client, version, address, status
    ):
        plain = without_the_check("get", address)

        response = client.get(address)

        assert response.status_code == plain.status_code == status
        assert response.get("Location") == plain.get("Location")
        assert not sent_to_the_page_that_asks(response)

    @pytest.mark.parametrize(
        "address",
        [
            pytest.param(lambda document: agreement_address(), id="page that asks"),
            pytest.param(
                lambda document: reverse(
                    "mvp_compliance:document", args=[document.slug]
                ),
                id="document",
            ),
            pytest.param(
                lambda document: reverse("mvp_compliance:agreed"), id="agreed list"
            ),
        ],
    )
    def test_a_stopped_user_is_served_the_pages_that_stay_reachable(
        self, client, stopped, version, address
    ):
        response = client.get(address(version.document))

        assert response.status_code == 200

    @pytest.mark.parametrize("name", ["account_logout", "logout", "admin:logout"])
    def test_a_stopped_user_can_sign_out(self, client, stopped, name):
        response = client.post(reverse(name))

        assert not sent_to_the_page_that_asks(response)

    def test_a_stopped_user_is_served_static_and_media_files(
        self, client, stopped, settings
    ):
        settings.STATIC_URL = "/assets/"
        settings.MEDIA_URL = "/uploads/"

        static = client.get("/assets/css/site.css")
        media = client.get("/uploads/logo.png")

        assert static.status_code == media.status_code == 200
        assert called == ["/assets/css/site.css", "/uploads/logo.png"]

    @pytest.mark.parametrize(
        "static_url",
        [None, "https://cdn.example.com/static/", "//cdn.example.com/static/"],
    )
    def test_a_static_url_that_is_not_a_path_on_this_site_covers_nothing(
        self, client, stopped, settings, static_url
    ):
        settings.STATIC_URL = static_url

        response = client.get("/static/css/site.css")

        assert sent_to_the_page_that_asks(response)
        assert called == []

    def test_an_address_that_only_starts_like_the_static_url_is_stopped(
        self, client, stopped
    ):
        response = client.get("/staticfiles/css/site.css")

        assert sent_to_the_page_that_asks(response)
        assert called == []

    def test_a_scheme_relative_static_url_is_not_matched_against_a_path(
        self, client, stopped, settings
    ):
        settings.STATIC_URL = "//cdn.example.com/static/"

        response = client.get("/elsewhere/", PATH_INFO="//cdn.example.com/static/a.css")

        assert sent_to_the_page_that_asks(response)

    @pytest.mark.parametrize("method", ["post", "put", "delete"])
    def test_a_submission_is_stopped_before_its_view_with_no_return_address(
        self, client, stopped, method
    ):
        response = getattr(client, method)("/elsewhere/?tab=2")

        assert sent_to_the_page_that_asks(response)
        assert urlsplit(response["Location"]).query == ""
        assert called == []

    def test_a_request_for_part_of_a_page_is_answered_with_a_redirect_header(
        self, client, stopped
    ):
        response = client.get("/elsewhere/?tab=2", headers={"HX-Request": "true"})

        assert response.status_code == 200
        assert response.content == b""
        assert response["HX-Redirect"] == agreement_address()
        assert "Location" not in response
        assert called == []

    def test_a_boosted_link_keeps_its_return_address(self, client, stopped):
        response = client.get(
            "/elsewhere/?tab=2",
            headers={"HX-Request": "true", "HX-Boosted": "true"},
        )

        assert response.status_code == 200
        assert "Location" not in response
        assert urlsplit(response["HX-Redirect"]).path == agreement_address()
        assert return_address(response["HX-Redirect"]) == ["/elsewhere/?tab=2"]

    def test_a_boosted_submission_carries_no_return_address(self, client, stopped):
        response = client.post(
            "/elsewhere/", headers={"HX-Request": "true", "HX-Boosted": "true"}
        )

        assert response.status_code == 200
        assert response["HX-Redirect"] == agreement_address()
        assert called == []

    def test_two_outstanding_enforced_documents_cost_one_redirect(
        self, client, stopped
    ):
        VersionFactory(document=DocumentFactory()).publish()

        response = client.get("/elsewhere/", follow=True)

        assert len(response.redirect_chain) == 1
        assert response.status_code == 200
        assert response.request["PATH_INFO"] == agreement_address()

    def test_an_address_that_resolves_to_nothing_is_stopped(self, client, stopped):
        response = client.get("/nowhere/")

        assert sent_to_the_page_that_asks(response)

    @pytest.mark.urls("tests.urls_own_agree_page")
    def test_a_page_that_asks_routed_outside_the_package_is_served(
        self, client, stopped
    ):
        response = client.get(agreement_address())

        assert response.status_code == 200

    def test_a_check_listed_ahead_of_the_user_lets_the_request_through(
        self, client, stopped, settings
    ):
        settings.MIDDLEWARE = [
            MIDDLEWARE,
            *(name for name in settings.MIDDLEWARE if name != MIDDLEWARE),
        ]

        response = client.get("/elsewhere/")

        assert response.status_code == 200

    @pytest.mark.urls("tests.urls_mvp_only")
    def test_a_project_that_does_not_mount_the_pages_is_not_redirected(
        self, client, stopped
    ):
        response = client.get(reverse("account-center"))

        assert response.status_code == 200


@pytest.mark.django_db
class TestAgreementCheckOff:
    def test_a_user_with_an_enforced_document_outstanding_is_served_everywhere(
        self, client, stopped
    ):
        assert Document.objects.enforced_outstanding_for(stopped).exists()

        response = client.get("/elsewhere/")

        assert response.status_code == 200
        assert called == ["/elsewhere/"]


@pytest.mark.django_db
@pytest.mark.usefixtures("check_on", "media_url_is_unset")
class TestAgreementCheckCost:
    def test_a_user_found_clear_adds_no_queries_to_the_requests_that_follow(
        self, client, version
    ):
        user = UserFactory()
        Acceptance.objects.record(user, version)
        address = reverse("mvp_compliance:document", args=[version.document.slug])
        client.force_login(user)
        plain = Client()
        plain.force_login(user)

        def requests_made(visitor):
            visitor.get(address)
            with CaptureQueriesContext(connection) as queries:
                assert visitor.get(address).status_code == 200
            return len(queries)

        with modify_settings(MIDDLEWARE={"remove": MIDDLEWARE}):
            without = requests_made(plain)
        with_the_check = requests_made(client)

        assert with_the_check == without

    def test_a_finding_is_kept_as_a_timestamp_in_the_session(self, client, db):
        client.force_login(UserFactory())
        before = timezone.now().timestamp()

        key = remember_finding(client)

        kept = client.session[key]
        assert isinstance(kept, float)
        assert before <= kept <= timezone.now().timestamp()

    def test_a_user_found_clear_is_not_asked_about_again_within_a_minute(
        self, client, db
    ):
        client.force_login(UserFactory())
        remember_finding(client)
        VersionFactory(document=DocumentFactory()).publish()

        with after(55):
            response = client.get("/elsewhere/")

        assert response.status_code == 200

    def test_a_user_found_clear_is_asked_again_after_a_minute(self, client, db):
        client.force_login(UserFactory())
        remember_finding(client)
        VersionFactory(document=DocumentFactory()).publish()

        with after(65):
            response = client.get("/elsewhere/")

        assert sent_to_the_page_that_asks(response)

    @pytest.mark.parametrize("kept", ["soon", {"at": 1}, None])
    def test_a_finding_that_is_not_a_number_is_treated_as_absent(
        self, client, db, kept
    ):
        client.force_login(UserFactory())
        key = remember_finding(client)
        session = client.session
        session[key] = kept
        session.save()
        VersionFactory(document=DocumentFactory()).publish()

        response = client.get("/elsewhere/")

        assert sent_to_the_page_that_asks(response)

    def test_a_finding_dated_in_the_future_is_treated_as_absent(self, client, db):
        client.force_login(UserFactory())
        key = remember_finding(client)
        session = client.session
        session[key] = timezone.now().timestamp() + 3600
        session.save()
        VersionFactory(document=DocumentFactory()).publish()

        response = client.get("/elsewhere/")

        assert sent_to_the_page_that_asks(response)

    def test_a_stopped_user_is_asked_about_on_every_request_and_writes_nothing(
        self, client, stopped
    ):
        before = dict(client.session)

        first = client.get("/elsewhere/")
        second = client.get("/elsewhere/")

        assert sent_to_the_page_that_asks(first)
        assert sent_to_the_page_that_asks(second)
        assert dict(client.session) == before
