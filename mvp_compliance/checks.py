"""System checks that report an agreement check that cannot work as configured."""

from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.core.checks import CheckMessage, Error
from django.urls import NoReverseMatch, reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

AGREEMENT_MIDDLEWARE = "mvp_compliance.middleware.AgreementMiddleware"


def check_agreement_middleware(app_configs, **kwargs) -> list[CheckMessage]:
    """Report a listed agreement check that would redirect nobody, or everybody.

    Registered from ``MvpComplianceConfig.ready()``. Nothing is reported while
    the project has not listed ``AgreementMiddleware`` in ``MIDDLEWARE``.

    Args:
        app_configs: The app configs being checked. Not used.
        **kwargs: The remaining arguments Django passes to every check.

    Returns:
        ``mvp_compliance.E001`` when the page that asks has no address, and
        ``mvp_compliance.E002`` when nothing that identifies the signed-in user
        comes before the middleware.
    """
    middleware = list(settings.MIDDLEWARE)
    if AGREEMENT_MIDDLEWARE not in middleware:
        return []
    errors: list[CheckMessage] = []
    try:
        reverse("mvp_compliance:agree")
    except NoReverseMatch:
        errors.append(
            Error(
                _("The page that asks a person to agree has no address."),
                hint=_("Add %(line)s to the project's URLconf.")
                % {"line": 'path("legal/", include("mvp_compliance.urls"))'},
                id="mvp_compliance.E001",
            )
        )
    if not any(
        identifies_the_user(name)
        for name in middleware[: middleware.index(AGREEMENT_MIDDLEWARE)]
    ):
        errors.append(
            Error(
                _("Nothing that identifies the signed-in user comes before the check."),
                hint=_("List %(check)s after %(authentication)s in MIDDLEWARE.")
                % {
                    "check": AGREEMENT_MIDDLEWARE,
                    "authentication": "django.contrib.auth.middleware."
                    "AuthenticationMiddleware",
                },
                id="mvp_compliance.E002",
            )
        )
    return errors


def identifies_the_user(name: str) -> bool:
    """Say whether the middleware listed as ``name`` is Django's or a subclass of it.

    Args:
        name: A dotted path from ``MIDDLEWARE``.

    Returns:
        Whether it is ``AuthenticationMiddleware`` or a subclass of it. A path
        that cannot be imported, or names a function, is not.
    """
    try:
        middleware = import_string(name)
    except ImportError:
        return False
    return isinstance(middleware, type) and issubclass(
        middleware, AuthenticationMiddleware
    )
