"""factory_boy factories for the document/version models.

One factory per model. Downstream tests build their fixtures on these
instead of hand-constructing documents and versions.
"""

import factory

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
