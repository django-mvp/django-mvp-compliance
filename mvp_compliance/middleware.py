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


class AgreementMiddleware:
    """Send a signed-in person to the page that asks, from any address on the site.

    A person is stopped when a document that is enforced is outstanding for
    them, whatever address they asked for. The pages that stay reachable are
    the ones ``is_reachable()`` lists. A visitor who is not signed in is never
    touched. Nothing is checked until the project lists this class in
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
            The response of the rest of the stack, or an answer that takes the
            person to the page that asks: for an htmx request a ``200`` with an
            ``HX-Redirect`` header, otherwise a redirect. A ``GET`` or ``HEAD``,
            and a boosted link, carry the address asked for as ``next``; a
            request that visiting an address would not repeat carries none.
            Only a finding that nothing stops the person is written to the
            session, and it is read back only when it is a number that is less
            than ``CLEAR_FINDING_SECONDS`` old. An account named in
            ``MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS``, and one that holds the
            ``mvp_compliance.skip_agreement`` permission, are let through
            and nothing is written for them: the permission is asked of a
            person only once they are known to be outstanding.
        """
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return self.get_response(request)
        found = request.session.get(CLEAR_SINCE_KEY)
        if (
            isinstance(found, int | float)
            and 0 <= timezone.now().timestamp() - found < CLEAR_FINDING_SECONDS
        ):
            return self.get_response(request)
        exempt = getattr(settings, "MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS", [])
        if user.get_username() in exempt:
            return self.get_response(request)
        if not Document.objects.enforced_outstanding_for(user).exists():
            request.session[CLEAR_SINCE_KEY] = timezone.now().timestamp()
            return self.get_response(request)
        if user.has_perm("mvp_compliance.skip_agreement"):
            return self.get_response(request)
        try:
            address = reverse("mvp_compliance:agree")
        except NoReverseMatch:
            return self.get_response(request)
        if self.is_reachable(request):
            return self.get_response(request)
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

    def is_reachable(self, request: HttpRequest) -> bool:
        """Say whether the address asked for is kept reachable.

        Args:
            request: The request being handled.

        Returns:
            Whether the address is the page that asks, one of this package's own
            pages, a sign-out address (``account_logout``, ``logout`` or
            ``admin:logout``), a path beneath ``STATIC_URL`` or ``MEDIA_URL``, or
            a path beneath an entry of
            ``MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS``. ``STATIC_URL`` and
            ``MEDIA_URL`` cover nothing when they are unset, are the site root,
            or name another host. An entry is compared with ``request.path_info``,
            ``"/"`` covers every address and an empty entry covers nothing.
            "Beneath" is read a path segment at a time.
        """
        if request.path == reverse("mvp_compliance:agree"):
            return True
        try:
            match = resolve(request.path_info)
        except Resolver404:
            pass
        else:
            if "mvp_compliance" in match.app_names or match.view_name in (
                "account_logout",
                "logout",
                "admin:logout",
            ):
                return True
        for url in (settings.STATIC_URL, settings.MEDIA_URL):
            if not url or url == get_script_prefix():
                continue
            parts = urlsplit(url)
            if parts.scheme or parts.netloc:
                continue
            root = url.rstrip("/")
            if request.path == root or request.path.startswith(f"{root}/"):
                return True
        for entry in getattr(settings, "MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS", []):
            root = entry.rstrip("/")
            if entry and (
                request.path_info == root or request.path_info.startswith(f"{root}/")
            ):
                return True
        return False
