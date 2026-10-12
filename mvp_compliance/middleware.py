"""The check that stops a signed-in person who has not agreed to what is enforced."""

from collections.abc import Callable
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.http.response import HttpResponseBase
from django.urls import NoReverseMatch, Resolver404, get_script_prefix, resolve, reverse
from django.utils import timezone

from mvp_compliance.models import Document

#: Where a clear finding is kept in the session: the time it was made, as a
#: POSIX timestamp. Signing in as somebody else flushes the session.
CLEAR_SINCE_KEY = "mvp_compliance_clear_since"

#: How many seconds a clear finding is remembered, so that the question is not
#: put to the database on every request.
CLEAR_FINDING_SECONDS = 60

#: The names a sign-out address is registered under by Django's admin,
#: django-mvp and Django's own ``LogoutView``.
SIGN_OUT_VIEW_NAMES = ("account_logout", "logout", "admin:logout")


class AgreementMiddleware:
    """Send a signed-in person to the page that asks, from any address on the site.

    A person is stopped when a document that is enforced is outstanding for
    them, whatever address they asked for. The pages that stay reachable are
    the ones listed on ``is_reachable()``. A visitor who is not signed in is
    never touched. Nothing is checked until the project lists this class in
    ``MIDDLEWARE``, after ``AuthenticationMiddleware``.

    Args:
        get_response: The next middleware or the view.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        """Let the request through, or answer it with the page that asks.

        Args:
            request: The request being handled.

        Returns:
            The response of the rest of the stack, or a redirect to the page
            that asks. Only a finding that nothing stops the person is written
            to the session.
        """
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return self.get_response(request)
        if self.is_remembered_clear(request):
            return self.get_response(request)
        if not Document.objects.enforced_outstanding_for(user).exists():
            request.session[CLEAR_SINCE_KEY] = timezone.now().timestamp()
            return self.get_response(request)
        try:
            address = reverse("mvp_compliance:agree")
        except NoReverseMatch:
            return self.get_response(request)
        if self.is_reachable(request):
            return self.get_response(request)
        return self.stop(request, address)

    def is_remembered_clear(self, request: HttpRequest) -> bool:
        """Say whether this person was found clear less than a minute ago.

        Args:
            request: The request being handled, with its session.

        Returns:
            Whether the session holds a number, and that much time has not
            passed since it. A value that is not a number is treated as absent.
        """
        found = request.session.get(CLEAR_SINCE_KEY)
        if not isinstance(found, int | float):
            return False
        return 0 <= timezone.now().timestamp() - found < CLEAR_FINDING_SECONDS

    def is_reachable(self, request: HttpRequest) -> bool:
        """Say whether the address asked for is kept reachable.

        Args:
            request: The request being handled.

        Returns:
            Whether the address is the page that asks, one of the package's own
            pages, a sign-out address, or a file under ``STATIC_URL`` or
            ``MEDIA_URL``.
        """
        if request.path == reverse("mvp_compliance:agree"):
            return True
        try:
            match = resolve(request.path_info)
        except Resolver404:
            pass
        else:
            if (
                "mvp_compliance" in match.app_names
                or match.view_name in SIGN_OUT_VIEW_NAMES
            ):
                return True
        return any(
            self.is_beneath(request.path, root)
            for root in (settings.STATIC_URL, settings.MEDIA_URL)
            if self.is_a_path_on_this_site(root)
        )

    @staticmethod
    def is_a_path_on_this_site(url: str | None) -> bool:
        """Say whether a setting such as ``STATIC_URL`` names a place on this site.

        Args:
            url: The setting's value.

        Returns:
            ``False`` when it is unset, the site root, which is what Django
            returns for an empty ``MEDIA_URL``, or an address on another host.
        """
        if not url or url == get_script_prefix():
            return False
        parts = urlsplit(url)
        return not parts.scheme and not parts.netloc

    @staticmethod
    def is_beneath(path: str, root: str) -> bool:
        """Say whether ``path`` is ``root`` or lies under it, a segment at a time.

        Args:
            path: The path of a request.
            root: A path such as ``/static/``.

        Returns:
            Whether ``path`` is ``root`` with or without its trailing slash, or
            continues it after a slash: ``/static/`` covers ``/static/a.css``
            and does not cover ``/staticfiles/a.css``.
        """
        root = root.rstrip("/")
        return path == root or path.startswith(f"{root}/")

    def stop(self, request: HttpRequest, address: str) -> HttpResponseBase:
        """Answer a request that is not let past.

        Args:
            request: The request being handled.
            address: The address of the page that asks.

        Returns:
            For an htmx request, a ``200`` that tells htmx to load the page that
            asks as a whole page. For anything else, a redirect to it. A ``GET``
            or ``HEAD``, and a boosted link, carry the address asked for as
            ``next``; a request that visiting an address would not repeat
            carries none.
        """
        returning = f"{address}?{urlencode({'next': request.get_full_path()})}"
        if request.headers.get("HX-Request") == "true":
            boosted = request.method == "GET" and (
                request.headers.get("HX-Boosted") == "true"
            )
            response = HttpResponse()
            response["HX-Redirect"] = returning if boosted else address
            return response
        if request.method in ("GET", "HEAD"):
            return HttpResponseRedirect(returning)
        return HttpResponseRedirect(address)
