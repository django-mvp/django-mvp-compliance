"""Sign-in for the demo project."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Accept an account's email address as well as its username.

    The demo's accounts are known by their email addresses, and django-mvp's
    stand-in sign-in page asks for a username, so either is accepted.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username and "@" in username:
            account = get_user_model()._default_manager.filter(
                email__iexact=username
            ).first()
            if account is not None:
                username = account.get_username()
        return super().authenticate(
            request, username=username, password=password, **kwargs
        )
