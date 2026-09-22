"""factory_boy factories for the models the test suite builds.

One factory per model. Downstream tests build their fixtures on these
instead of hand-constructing documents, versions and users.
"""

import factory
from django.contrib.auth import get_user_model

from mvp_compliance.models import Document, Version


class DocumentFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`Document` with an app-wide-unique name."""

    class Meta:
        model = Document

    name = factory.Sequence(lambda n: f"Document {n}")


class VersionFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`Version`, auto-creating its owning document.

    ``number`` is left unset — the model assigns it in ``save()``.
    """

    class Meta:
        model = Version

    document = factory.SubFactory(DocumentFactory)
    markdown = factory.Sequence(lambda n: f"Wording {n}")


class UserFactory(factory.django.DjangoModelFactory):
    """Build a saved user of the project's own user model.

    Staff status and permissions are overridden at the call site rather than
    by subclassing this — ``UserFactory(is_staff=True)``, and permissions
    added afterwards. The admin tests need several permission sets and a
    factory per set would be a factory per test.
    """

    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"person{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@example.com")
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set a usable password, so the test client can sign this user in."""
        if not create:
            return
        self.set_password(extracted or "password")
        self.save(update_fields=["password"])
