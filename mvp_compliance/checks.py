"""System checks that report an agreement check that cannot work as configured."""

from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.core.checks import CheckMessage, Error
from django.urls import NoReverseMatch, reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

AGREEMENT_MIDDLEWARE = "mvp_compliance.middleware.AgreementMiddleware"

#: The settings that are lists of strings, which a bare string would be read
#: from a character at a time.
LIST_SETTINGS = (
    "MVP_COMPLIANCE_AGREEMENT_EXEMPT_URLS",
    "MVP_COMPLIANCE_AGREEMENT_EXEMPT_USERS",
)


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
        comes before the middleware, ``mvp_compliance.E003`` for each
        setting that is a list and has been given as a string, and
        ``mvp_compliance.E004`` when the interval between checks is not a
        number.
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
    for name in LIST_SETTINGS:
        if isinstance(getattr(settings, name, []), str):
            errors.append(
                Error(
                    _("%(setting)s is a string, and has to be a list.")
                    % {"setting": name},
                    hint=_("Write it as a list, even for one entry: %(example)s.")
                    % {"example": f'{name} = ["..."]'},
                    id="mvp_compliance.E003",
                )
            )
    interval = getattr(settings, "MVP_COMPLIANCE_AGREEMENT_CHECK_INTERVAL", 60)
    if isinstance(interval, bool) or not isinstance(interval, int | float):
        errors.append(
            Error(
                _("%(setting)s is not a number.")
                % {"setting": "MVP_COMPLIANCE_AGREEMENT_CHECK_INTERVAL"},
                hint=_("Give it as a number of seconds, such as %(example)s.")
                % {"example": "60"},
                id="mvp_compliance.E004",
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
