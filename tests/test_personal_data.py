"""Tests for mvp_compliance.personal_data."""

import pytest
from django.core.files.base import ContentFile
from django.utils import translation
from django.utils.functional import Promise
from mvp_compliance.personal_data import (
    CopiedFile,
    PersonalDataSection,
    get_personal_data,
)

from tests.factories import NoteFactory, TopicFactory, UserFactory
from tests.kinds import Bare, Custom, Notes
from tests.models import Note


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def column(section, name):
    """The values of one column of ``section``, in row order."""
    names = [column_name for column_name, _label in section.columns]
    return [row[names.index(name)] for row in section.rows]


@pytest.mark.django_db
class TestCollect:
    def test_it_collects_that_users_rows_only_in_queryset_order(self, user):
        NoteFactory(owner=user, title="Second")
        NoteFactory(owner=user, title="First")
        NoteFactory(owner=UserFactory(), title="Somebody else's")

        section = Notes().collect(user)

        assert column(section, "title") == ["First", "Second"]

    def test_the_section_carries_the_kinds_own_description_of_itself(self, user):
        kind = Notes()

        section = kind.collect(user)

        assert section.key == kind.key
        assert section.heading == kind.heading
        assert section.description == kind.description
        assert section.single is kind.single
        assert section.template_name == kind.template_name

    def test_the_key_is_the_class_name_in_lower_case(self):
        assert Notes().key == "notes"

    def test_the_columns_are_the_declared_fields_in_order(self, user):
        section = Notes().collect(user)

        assert [name for name, _label in section.columns] == Notes.fields

    def test_a_label_is_the_fields_verbose_name_translated_when_it_is_read(self, user):
        section = Notes().collect(user)
        labels = dict(section.columns)

        with translation.override("de"):
            assert str(labels["title"]) == "Titel"
        with translation.override("en"):
            assert str(labels["title"]) == "Title"

    def test_a_label_is_kept_lazy(self, user):
        section = Notes().collect(user)

        assert all(isinstance(label, Promise) for _name, label in section.columns)

    def test_a_field_with_choices_yields_its_display_value(self, user):
        NoteFactory(owner=user, status=Note.Status.SHARED)

        section = Notes().collect(user)

        assert column(section, "status") == [Note.Status.SHARED.label]

    def test_a_relation_yields_its_str(self, user):
        topic = TopicFactory(name="Fieldwork")
        NoteFactory(owner=user, topic=topic)

        section = Notes().collect(user)

        assert column(section, "topic") == [str(topic)]

    def test_an_empty_value_yields_none(self, user):
        NoteFactory(owner=user, topic=None, summary="")

        section = Notes().collect(user)

        assert column(section, "topic") == [None]
        assert column(section, "summary") == [None]

    def test_any_other_value_is_yielded_as_stored(self, user):
        NoteFactory(owner=user, summary="Soil samples, plot 4")

        section = Notes().collect(user)

        assert column(section, "summary") == ["Soil samples, plot 4"]

    def test_a_file_field_with_a_file_yields_a_copied_file(self, user, media_root):
        note = NoteFactory(
            owner=user, attachment=ContentFile(b"readings", name="readings.txt")
        )

        section = Notes().collect(user)

        (copied,) = column(section, "attachment")
        assert isinstance(copied, CopiedFile)
        assert copied.name == note.attachment.name.rsplit("/", 1)[-1]
        assert copied.path == f"files/notes/{note.pk}/{copied.name}"
        assert copied.field_file.name == note.attachment.name

    def test_two_records_with_same_named_files_get_distinct_paths(
        self, user, media_root
    ):
        first = NoteFactory(owner=user, attachment=ContentFile(b"1", name="same.txt"))
        second = NoteFactory(owner=user, attachment=ContentFile(b"2", name="same.txt"))

        section = Notes().collect(user)

        paths = [copied.path for copied in column(section, "attachment")]
        assert len(set(paths)) == 2
        assert {f"files/notes/{first.pk}/", f"files/notes/{second.pk}/"} == {
            path.rsplit("/", 1)[0] + "/" for path in paths
        }

    def test_an_empty_file_field_yields_none(self, user):
        NoteFactory(owner=user, attachment="")

        section = Notes().collect(user)

        assert column(section, "attachment") == [None]

    def test_a_kind_that_does_not_say_whose_rows_to_read_is_refused(self, user):
        with pytest.raises(NotImplementedError):
            Bare().collect(user)

    def test_a_kind_overriding_collect_returns_its_own_section(self, user):
        section = Custom().collect(user)

        assert isinstance(section, PersonalDataSection)
        assert section.key == "custom"
        assert column(section, "greeting") == [f"Hello, {user.get_username()}"]


class TestGetPersonalData:
    def test_it_is_none_when_the_project_declares_nothing(self):
        assert get_personal_data() is None

    def test_an_empty_declaration_is_an_empty_list_not_none(self, settings):
        settings.MVP_COMPLIANCE_PERSONAL_DATA = []

        assert get_personal_data() == []

    def test_it_returns_an_instance_of_each_declared_kind_in_order(self, settings):
        settings.MVP_COMPLIANCE_PERSONAL_DATA = [
            "tests.kinds.Custom",
            "tests.kinds.Notes",
        ]

        kinds = get_personal_data()

        assert [type(kind) for kind in kinds] == [Custom, Notes]
