"""A second module of kinds, so two kinds can share a class name."""

from mvp_compliance.personal_data import PersonalData
from tests.models import Topic


class Notes(PersonalData):
    """A different kind with the same key as ``tests.kinds.Notes``."""

    model = Topic
    fields = ["name"]

    def get_queryset(self, user):
        return Topic.objects.all()
