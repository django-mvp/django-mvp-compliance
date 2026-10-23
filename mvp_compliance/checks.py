"""System checks that report an agreement check that cannot work as configured."""

from django.apps import apps
from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.core.checks import CheckMessage, Error
from django.core.exceptions import FieldDoesNotExist
from django.urls import NoReverseMatch, reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from mvp_compliance.personal_data import AGREEMENTS, PersonalData

AGREEMENT_MIDDLEWARE = "mvp_compliance.middleware.AgreementMiddleware"
ACCOUNT_MIDDLEWARE = "allauth.account.middleware.AccountMiddleware"

SETTING = "MVP_COMPLIANCE_PERSONAL_DATA"

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


def check_personal_data(app_configs, **kwargs) -> list[CheckMessage]:
    """Report a declaration of personal data that cannot be read or confirmed.

    Registered from ``MvpComplianceConfig.ready()``. Nothing is reported while
    the project has not set ``MVP_COMPLIANCE_PERSONAL_DATA``.

    Args:
        app_configs: The app configs being checked. Not used.
        **kwargs: The remaining arguments Django passes to every check.

    Returns:
        ``mvp_compliance.E005`` when the setting is a string or not a list,
        ``mvp_compliance.E006`` for each path that does not name a
        ``PersonalData`` subclass and for each kind whose key an earlier kind
        already has, ``mvp_compliance.E007`` for each field a kind lists that
        its model lacks, ``mvp_compliance.E008`` for each part of
        django-allauth's account app the page needs and the project lacks, and
        ``mvp_compliance.E009`` for each kind that does not say how it is
        erased once another does, and for each ``erasure`` that is neither
        constant.
    """
    paths = getattr(settings, "MVP_COMPLIANCE_PERSONAL_DATA", None)
    if paths is None:
        return []
    if not isinstance(paths, list | tuple):
        return [
            Error(
                _("%(setting)s is not a list.") % {"setting": SETTING},
                hint=_(
                    "Write it as a list of dotted paths, even for one kind: %(example)s."
                )
                % {"example": f'{SETTING} = ["accounts.personal_data.Profile"]'},
                id="mvp_compliance.E005",
            )
        ]
    errors: list[CheckMessage] = []
    imported: list[tuple[str, PersonalData]] = []
    # The package's own section is always in a copy, so its key is taken.
    kinds: dict[str, str] = {
        AGREEMENTS: "mvp_compliance.personal_data.AgreementsPersonalData"
    }
    for path in paths:
        kind = import_kind(path)
        if kind is None:
            errors.append(
                Error(
                    _("%(path)s does not name a PersonalData subclass.")
                    % {"path": path},
                    hint=_("Name a class that subclasses %(base)s.")
                    % {"base": "mvp_compliance.personal_data.PersonalData"},
                    id="mvp_compliance.E006",
                )
            )
            continue
        instance = kind()
        imported.append((path, instance))
        key = instance.key
        if key in kinds:
            errors.append(
                Error(
                    _("%(first)s and %(second)s have the same key, %(key)s.")
                    % {"first": kinds[key], "second": path, "key": key},
                    hint=_("Set a different key on one of them."),
                    id="mvp_compliance.E006",
                )
            )
        kinds.setdefault(key, path)
        model = kind.model
        if model is None:
            continue
        for name in kind.fields:
            try:
                model._meta.get_field(name)
            except FieldDoesNotExist:
                errors.append(
                    Error(
                        _("%(path)s lists %(field)s, which %(model)s does not have.")
                        % {"path": path, "field": name, "model": model.__name__},
                        hint=_("Remove it from fields, or correct its spelling."),
                        id="mvp_compliance.E007",
                    )
                )
    return errors + check_erasure(imported) + check_account_app()


def check_erasure(kinds: list[tuple[str, PersonalData]]) -> list[CheckMessage]:
    """Report a declaration that says how some kinds are erased and not others.

    Args:
        kinds: Each declared kind with the path it was declared by.

    Returns:
        ``mvp_compliance.E009`` for each kind that does not say how it is
        erased while another does, and for each ``erasure`` that is neither
        ``PersonalData.DELETE`` nor ``PersonalData.WITH_ACCOUNT``. Nothing
        while no kind says anything.
    """
    if not any(kind.says_how_erased for _path, kind in kinds):
        return []
    constants = (PersonalData.DELETE, PersonalData.WITH_ACCOUNT)
    errors: list[CheckMessage] = []
    for path, kind in kinds:
        if kind.erasure is not None and kind.erasure not in constants:
            message = _("%(path)s sets erasure to something other than %(constants)s.")
        elif not kind.says_how_erased:
            message = _("%(path)s does not say how its records are deleted.")
        else:
            continue
        errors.append(
            Error(
                message
                % {"path": path, "constants": "PersonalData.DELETE or WITH_ACCOUNT"},
                hint=_(
                    "Set erasure to PersonalData.DELETE or PersonalData.WITH_ACCOUNT, "
                    "or override erase()."
                ),
                id="mvp_compliance.E009",
            )
        )
    return errors


def check_account_app() -> list[CheckMessage]:
    """Report what django-allauth's account app lacks for confirming a person.

    Returns:
        ``mvp_compliance.E008`` when ``allauth.account`` is not installed, and
        again when its middleware is not listed.
    """
    errors: list[CheckMessage] = []
    if not apps.is_installed("allauth.account"):
        errors.append(
            Error(
                _("The page that gives a person a copy of their data needs allauth."),
                hint=_("Install the extra %(extra)s and add %(app)s to INSTALLED_APPS.")
                % {
                    "extra": "django-mvp-compliance[personal-data]",
                    "app": "allauth.account",
                },
                id="mvp_compliance.E008",
            )
        )
    if ACCOUNT_MIDDLEWARE not in settings.MIDDLEWARE:
        errors.append(
            Error(
                _(
                    "The page that gives a person a copy of their data needs allauth's middleware."
                ),
                hint=_("Add %(middleware)s to MIDDLEWARE.")
                % {"middleware": ACCOUNT_MIDDLEWARE},
                id="mvp_compliance.E008",
            )
        )
    return errors


def import_kind(path: object) -> type[PersonalData] | None:
    """Import the kind a path in the setting names.

    Args:
        path: An entry of ``MVP_COMPLIANCE_PERSONAL_DATA``.

    Returns:
        The class, or ``None`` when the entry is not a string, cannot be
        imported or is not a ``PersonalData`` subclass.
    """
    if not isinstance(path, str):
        return None
    try:
        kind = import_string(path)
    except ImportError:
        return None
    if isinstance(kind, type) and issubclass(kind, PersonalData):
        return kind
    return None


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
