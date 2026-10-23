"""Tests for mvp_compliance.personal_data."""

import io
import json
import zipfile
from html.parser import HTMLParser

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone, translation
from django.utils.functional import Promise
from django.utils.module_loading import import_string

from mvp_compliance.models import Acceptance
from mvp_compliance.personal_data import (
    AgreementsPersonalData,
    CopiedFile,
    PersonalDataCopy,
    PersonalDataSection,
    get_personal_data,
)
from tests.factories import (
    AcceptanceFactory,
    NoteFactory,
    TopicFactory,
    UserFactory,
    VersionFactory,
)
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


class CopyReader(HTMLParser):
    """Reads a copy's ``index.html``: each section's records, by ``data-`` hook."""

    VOID = {"br", "hr", "img", "input", "link", "meta"}

    def __init__(self, html):
        super().__init__()
        self.sections = {}
        self.own = {}
        self.section = None
        self.field = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-section" in attrs:
            self.section = attrs["data-section"]
            self.sections[self.section] = []
        if "data-record" in attrs:
            self.sections[self.section].append({})
        if "data-own-template" in attrs:
            self.own[attrs["data-own-template"]] = True
        if self.field is not None and tag not in self.VOID:
            self.field["depth"] += 1
        if "data-field" in attrs:
            self.field = {"name": attrs["data-field"], "depth": 1, "text": []}

    def handle_data(self, data):
        if self.field is not None:
            self.field["text"].append(data)

    def handle_endtag(self, tag):
        if self.field is None:
            return
        self.field["depth"] -= 1
        if self.field["depth"] == 0:
            text = "".join(self.field["text"]).strip()
            self.sections[self.section][-1][self.field["name"]] = text
            self.field = None


def open_copy(user, *paths, made_at=None):
    """Build a copy of what the kinds at ``paths`` and the agreements hold about ``user``."""
    kinds = [*(import_string(path)() for path in paths), AgreementsPersonalData()]
    copy = PersonalDataCopy(
        user,
        PersonalDataCopy.collect(user, kinds),
        made_at or timezone.now(),
        "The site",
        "light",
    )
    buffer = io.BytesIO()
    copy.write(buffer)
    return zipfile.ZipFile(buffer)


def data_of(archive):
    return json.loads(archive.read("data.json"))


def section_of(archive, key):
    (section,) = [s for s in data_of(archive)["sections"] if s["key"] == key]
    return section


@pytest.mark.django_db
class TestPersonalDataCopy:
    def test_the_archive_holds_the_readable_page_the_data_and_each_file_at_its_path(
        self, user, stored_files
    ):
        note = NoteFactory(
            owner=user, attachment=ContentFile(b"the bytes", name="report.txt")
        )

        archive = open_copy(user, "tests.kinds.Notes")

        path = f"files/notes/{note.pk}/report.txt"
        assert set(archive.namelist()) == {"index.html", "data.json", path}
        assert archive.read(path) == b"the bytes"

    def test_two_files_with_the_same_name_are_both_kept(self, user, stored_files):
        first = NoteFactory(owner=user, attachment=ContentFile(b"one", name="a.txt"))
        second = NoteFactory(owner=user, attachment=ContentFile(b"two", name="a.txt"))

        archive = open_copy(user, "tests.kinds.Notes")

        assert archive.read(f"files/notes/{first.pk}/a.txt") == b"one"
        assert archive.read(f"files/notes/{second.pk}/a.txt") == b"two"

    def test_the_data_holds_every_kind_in_declared_order_then_the_agreements(
        self, user
    ):
        archive = open_copy(user, "tests.kinds.Custom", "tests.kinds.Notes")

        keys = [section["key"] for section in data_of(archive)["sections"]]

        assert keys == ["custom", "notes", "agreements"]

    def test_the_data_says_when_it_was_made_and_for_whom(self, user):
        made_at = timezone.now().replace(microsecond=0)

        data = data_of(open_copy(user, "tests.kinds.Notes", made_at=made_at))

        assert data["made_at"] == made_at.isoformat().replace("+00:00", "Z")
        assert data["person"] == user.get_username()

    def test_each_record_is_keyed_by_the_field_name_and_a_file_is_its_path(
        self, user, stored_files
    ):
        topic = TopicFactory(name="Wildlife")
        note = NoteFactory(
            owner=user,
            title="Heron",
            topic=topic,
            attachment=ContentFile(b"x", name="heron.txt"),
        )

        section = section_of(open_copy(user, "tests.kinds.Notes"), "notes")

        (record,) = section["records"]
        assert record == {
            "title": "Heron",
            "status": "Draft",
            "topic": "Wildlife",
            "summary": None,
            "attachment": f"files/notes/{note.pk}/heron.txt",
        }
        assert list(section["fields"]) == Notes.fields

    def test_the_readable_page_holds_the_same_records_as_the_data(self, user):
        NoteFactory(owner=user, title="Second", summary="Later")
        NoteFactory(owner=user, title="First", summary="Earlier")
        archive = open_copy(user, "tests.kinds.Notes")

        read = CopyReader(archive.read("index.html").decode())

        shown = [
            {name: record[name] for name in ("title", "status", "summary")}
            for record in read.sections["notes"]
        ]
        held = [
            {name: record[name] for name in ("title", "status", "summary")}
            for record in section_of(archive, "notes")["records"]
        ]
        assert shown == held
        assert [record["title"] for record in held] == ["First", "Second"]

    def test_the_agreements_hold_each_acceptance_with_its_exact_wording(self, user):
        old = VersionFactory(markdown="Old *wording*")
        old.publish()
        AcceptanceFactory(user=user, version=old)
        new = VersionFactory(document=old.document, markdown="New wording")
        new.publish()
        AcceptanceFactory(user=user, version=new)
        old.refresh_from_db()
        new.refresh_from_db()
        archive = open_copy(user)

        records = section_of(archive, "agreements")["records"]
        page = archive.read("index.html").decode()

        assert {record["wording"] for record in records} == {old.html, new.html}
        assert {record["version"] for record in records} == {old.number, new.number}
        assert {record["document"] for record in records} == {old.document.name}
        assert all(record["accepted_at"] for record in records)
        assert old.html in page
        assert new.html in page
        assert len(CopyReader(page).sections["agreements"]) == 2

    def test_a_kind_with_no_rows_and_no_agreements_are_present_and_empty(self, user):
        archive = open_copy(user, "tests.kinds.Notes")

        read = CopyReader(archive.read("index.html").decode())

        for key in ("notes", "agreements"):
            assert section_of(archive, key)["records"] == []
            assert read.sections[key] == []

    def test_a_copy_holds_nothing_of_another_person(self, user, stored_files):
        other = UserFactory()
        NoteFactory(
            owner=other, title="Not yours", attachment=ContentFile(b"x", name="b.txt")
        )
        version = VersionFactory()
        version.publish()
        AcceptanceFactory(user=other, version=version)
        NoteFactory(owner=user, title="Yours")

        archive = open_copy(user, "tests.kinds.Notes")

        assert set(archive.namelist()) == {"index.html", "data.json"}
        assert "Not yours" not in archive.read("index.html").decode()
        assert "Not yours" not in archive.read("data.json").decode()
        assert section_of(archive, "agreements")["records"] == []

    def test_a_kind_with_its_own_template_is_drawn_with_it_and_keeps_the_standard_data(
        self, user
    ):
        NoteFactory(owner=user, title="Heron")
        archive = open_copy(user, "tests.kinds.OwnTemplate")

        read = CopyReader(archive.read("index.html").decode())

        assert "owntemplate" in read.own
        assert section_of(archive, "owntemplate")["records"][0]["title"] == "Heron"

    def test_building_a_copy_writes_no_row(self, user):
        NoteFactory(owner=user)
        before = (Note.objects.count(), Acceptance.objects.count())

        open_copy(user, "tests.kinds.Notes")

        assert (Note.objects.count(), Acceptance.objects.count()) == before
