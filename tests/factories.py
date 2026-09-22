"""factory_boy factories for the document/version models and the test user.

One factory per model. Downstream tests build their fixtures on these
instead of hand-constructing documents and versions.
"""

import factory
from django.contrib.auth import get_user_model

from mvp_compliance.models import Document, Version


class UserFactory(factory.django.DjangoModelFactory):
    """Build a saved instance of the configured user model."""

    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f"user-{n}")


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
