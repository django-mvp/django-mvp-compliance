"""What a project declares it holds about a person, and how it is read.

A project lists dotted paths to ``PersonalData`` subclasses in
``MVP_COMPLIANCE_PERSONAL_DATA``. Each one is a kind of record the project
holds about a person. Reading a kind for one user gives a section.
"""

import json
import os
import shutil
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import IO, Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.fields.files import FieldFile
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import Promise
from django.utils.module_loading import import_string
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _

from mvp_compliance import records
from mvp_compliance.exceptions import PersonalDataError
from mvp_compliance.models import Acceptance

#: The key of the package's own section, always the copy's last.
AGREEMENTS = "agreements"


@dataclass(frozen=True)
class CopiedFile:
    """A file a copy holds, and where in the copy it is placed.

    Attributes:
        path: Where the file sits inside the copy, ``files/<key>/<pk>/<name>``.
        name: The file's base name, as the person knows it.
        field_file: The stored file, opened only when the copy is written.
    """

    path: str
    name: str
    field_file: FieldFile


@dataclass(frozen=True)
class PersonalDataSection:
    """One kind's records about one person.

    Attributes:
        key: The kind's key: its anchor in the copy and its folder for files.
        heading: What the section is called.
        description: A sentence saying what is in it.
        single: Whether a person has one record of the kind, not a list.
        template_name: The template that draws the section, or ``None`` for
            the standard table.
        columns: ``(name, label)`` for each field, in order.
        rows: One tuple of values per record, in the order of ``columns``.
        kind: The dotted path of the kind that produced it, set when a copy
            collects it and used to name the kind when it fails.
    """

    key: str
    heading: str | Promise
    columns: tuple[tuple[str, str | Promise], ...]
    rows: tuple[tuple[Any, ...], ...]
    description: str | Promise = ""
    single: bool = False
    template_name: str | None = None
    kind: str = ""


class PersonalData:
    """A kind of record the project holds about a person.

    Subclass it, name a ``model`` and its ``fields``, and say whose rows are
    whose in ``get_queryset``. Override ``collect`` for data that is not one
    queryset.

    Attributes:
        heading: What the kind is called to the person.
        description: A sentence saying what the kind holds.
        model: The model the rows come from.
        fields: The model's field names to include, in order. A ``FileField``
            named here puts its file in the copy.
        single: Whether a person has one record of the kind, not a list.
        template_name: A template that draws the kind in the readable copy in
            place of the standard table.
    """

    heading: str | Promise = ""
    description: str | Promise = ""
    model: type[models.Model] | None = None
    fields: list[str] = []
    single: bool = False
    template_name: str | None = None

    @property
    def key(self) -> str:
        """The kind's key: the class name in lower case unless a subclass sets one."""
        return type(self).__name__.lower()

    def get_queryset(self, user: AbstractBaseUser) -> models.QuerySet:
        """Return the rows the project holds about ``user``.

        Args:
            user: The person whose rows are wanted.

        Returns:
            The queryset, in the order the rows are to appear.

        Raises:
            NotImplementedError: Always, until a subclass overrides it. Which
                field points at the person is the project's knowledge.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must say whose rows are whose in get_queryset()."
        )

    def collect(self, user: AbstractBaseUser) -> PersonalDataSection:
        """Read the kind's rows about ``user`` into a section.

        Args:
            user: The person whose rows are wanted.

        Returns:
            One row per record, with a value for each name in ``fields``.
        """
        queryset = self.get_queryset(user)
        fields: list[Any] = [
            self.model._meta.get_field(name)  # type: ignore[union-attr]
            for name in self.fields
        ]
        return PersonalDataSection(
            key=self.key,
            heading=self.heading,
            description=self.description,
            single=self.single,
            template_name=self.template_name,
            columns=tuple((field.name, field.verbose_name) for field in fields),
            rows=tuple(
                tuple(self.get_value(record, field) for field in fields)
                for record in queryset
            ),
        )

    def get_value(self, record: models.Model, field: Any) -> Any:
        """Return what ``record`` holds in ``field``, as a person reads it.

        Args:
            record: One row.
            field: The model field to read.

        Returns:
            A ``CopiedFile`` for a file, the choice's display value for a field
            with choices, ``str()`` for a relation, ``None`` for an empty value
            and the stored value otherwise.
        """
        value = getattr(record, field.name)
        if isinstance(field, models.FileField):
            return self.get_copied_file(record, field, value)
        if value is None or value == "":
            return None
        if field.choices:
            return getattr(record, f"get_{field.name}_display")()
        if field.is_relation:
            return str(value)
        return value

    def get_copied_file(
        self, record: models.Model, field: models.Field, field_file: FieldFile
    ) -> CopiedFile | None:
        """Place a stored file inside the copy.

        Its path is ``files/<key>/<record key>/<field name>/<file name>``, so two
        fields or two records holding files of one name never share a path, and
        a record key is made safe to use as a folder name.

        Args:
            record: The row the file belongs to.
            field: The file field the value came from.
            field_file: The row's value for the file field.

        Returns:
            The file with its path in the copy, or ``None`` when the row has no file.
        """
        if not field_file:
            return None
        name = os.path.basename(str(field_file.name))
        folder = get_valid_filename(str(record.pk)) if str(record.pk) else "_"
        return CopiedFile(
            path=f"files/{self.key}/{folder}/{field.name}/{name}",
            name=name,
            field_file=field_file,
        )


class AgreementsPersonalData(PersonalData):
    """The documents a person agreed to, which the package holds itself.

    Never declared: a copy always ends with it.
    """

    heading = _("Documents you agreed to")
    description = _(
        "Each version of this site's documents you agreed to, when you agreed, "
        "and the wording you were shown."
    )

    @property
    def key(self) -> str:
        """The section's key, ``agreements``."""
        return AGREEMENTS

    def collect(self, user: AbstractBaseUser) -> PersonalDataSection:
        """Read the person's acceptances, each with the wording stored at publication.

        Args:
            user: The person whose acceptances are wanted.

        Returns:
            One row per acceptance: document, version, time and wording.
        """
        (section,) = records.produce(Acceptance.subject_of(user)).sections
        return PersonalDataSection(
            key=self.key,
            heading=self.heading,
            description=self.description,
            columns=(
                ("document", _("Document")),
                ("version", _("Version")),
                ("accepted_at", _("Agreed on")),
                ("wording", _("The wording you agreed to")),
            ),
            rows=tuple(
                (entry.document, entry.version, entry.accepted_at, entry.wording)
                for entry in section.entries
            ),
        )


def get_personal_data() -> list[PersonalData] | None:
    """Read the kinds the project declares.

    Returns:
        An instance of each kind in the order declared in
        ``MVP_COMPLIANCE_PERSONAL_DATA``: ``None`` while the setting is absent
        and ``[]`` when it is empty.
    """
    paths = getattr(settings, "MVP_COMPLIANCE_PERSONAL_DATA", None)
    if paths is None:
        return None
    return [import_string(path)() for path in paths]


class PersonalDataCopy:
    """A person's copy: a readable page, the same records as data, and their files.

    Attributes:
        user: The person the copy is for.
        sections: What each kind holds about them, in the order they appear.
        made_at: When the copy was made.
        site_name: What the readable page calls the site.
        theme: The theme the readable page is drawn in.
    """

    def __init__(
        self,
        user: AbstractBaseUser,
        sections: list[PersonalDataSection],
        made_at: datetime,
        site_name: str,
        theme: str,
    ) -> None:
        self.user = user
        self.sections = sections
        self.made_at = made_at
        self.site_name = site_name
        self.theme = theme

    @staticmethod
    def collect(
        user: AbstractBaseUser, kinds: list[PersonalData]
    ) -> list[PersonalDataSection]:
        """Read every kind's records about ``user``, before anything is written.

        Args:
            user: The person whose records are wanted.
            kinds: The kinds to read, in the order they are to appear.

        Returns:
            One section per kind, in the same order.

        Raises:
            PersonalDataError: When a kind cannot read its records.
        """
        sections = []
        for kind in kinds:
            path = f"{type(kind).__module__}.{type(kind).__qualname__}"
            with PersonalDataCopy.guard(path):
                sections.append(replace(kind.collect(user), kind=path))
        return sections

    @staticmethod
    @contextmanager
    def guard(kind: str) -> Iterator[None]:
        """Name the kind that fails, whatever the failure.

        Args:
            kind: The dotted path of the kind being read, written or drawn.

        Raises:
            PersonalDataError: When the block raises, from the original error.
        """
        try:
            yield
        except PersonalDataError:
            raise
        except Exception as error:
            raise PersonalDataError(kind) from error

    def write(self, file: IO[bytes]) -> None:
        """Write the copy as a zip archive.

        Args:
            file: A seekable binary file to write the archive to.
        """
        with zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("index.html", self.get_page())
            archive.writestr("data.json", self.get_json())
            for section in self.sections:
                for row in section.rows:
                    for value in row:
                        if isinstance(value, CopiedFile):
                            with (
                                self.guard(section.kind),
                                value.field_file.open("rb") as source,
                                archive.open(
                                    value.path, "w", force_zip64=True
                                ) as target,
                            ):
                                shutil.copyfileobj(source, target)

    def get_json(self) -> str:
        """Return ``data.json``, each section encoded under its kind's guard.

        A value a kind hands back that JSON cannot hold fails as that kind.

        Returns:
            The JSON text.
        """
        data = self.get_data()
        for section, encoded in zip(self.sections, data["sections"], strict=True):
            with self.guard(section.kind):
                json.dumps(encoded, cls=DjangoJSONEncoder)
        return json.dumps(data, cls=DjangoJSONEncoder, indent=2, ensure_ascii=False)

    def get_data(self) -> dict[str, Any]:
        """Return the copy as data: every kind, each record keyed by field name.

        Returns:
            The structure written to ``data.json``. A file is its path in the copy.
        """
        return {
            "made_at": self.made_at,
            "person": self.user.get_username(),
            "sections": [
                {
                    "key": section.key,
                    "heading": str(section.heading),
                    "fields": {name: str(label) for name, label in section.columns},
                    "records": [
                        {
                            name: value.path if isinstance(value, CopiedFile) else value
                            for (name, _label), value in zip(
                                section.columns, row, strict=True
                            )
                        }
                        for row in section.rows
                    ],
                }
                for section in self.sections
            ],
        }

    def get_page(self) -> str:
        """Draw the readable page, with the site's stylesheet inline.

        Returns:
            The page's HTML.
        """
        path = finders.find("css/django-mvp.css")
        if not isinstance(path, str):
            raise ImproperlyConfigured("django-mvp's stylesheet cannot be found.")
        with open(path, encoding="utf-8") as stylesheet:
            css = stylesheet.read()
        return render_to_string(
            "mvp_compliance/copy/index.html",
            {
                "css": css,
                "theme": self.theme,
                "site_name": self.site_name,
                "made_at": self.made_at,
                "person": self.user.get_username(),
                "sections": [self.get_section(section) for section in self.sections],
            },
        )

    def get_section(self, section: PersonalDataSection) -> dict[str, Any]:
        """Describe one section for the readable page.

        Args:
            section: What one kind holds.

        Returns:
            What the page's template draws: the section's labels, its rows as
            ``(name, label, value)`` and, for a kind with its own template, that
            template's output.
        """
        rows = [
            [
                (name, label, self.get_value(value))
                for (name, label), value in zip(section.columns, row, strict=True)
            ]
            for row in section.rows
        ]
        acceptances = section.key == AGREEMENTS
        names = [name for name, _label in section.columns]
        rendered = ""
        if section.template_name and section.rows and not acceptances:
            with self.guard(section.kind):
                rendered = render_to_string(
                    section.template_name, {"section": section, "user": self.user}
                )
        return {
            "slug": section.key,
            "heading": section.heading,
            "description": section.description,
            "single": section.single,
            "labels": [label for _name, label in section.columns],
            "rows": rows,
            "records": (
                [dict(zip(names, row, strict=True)) for row in section.rows]
                if acceptances
                else rows
            ),
            "rendered": rendered,
            "acceptances": acceptances,
        }

    @staticmethod
    def get_value(value: Any) -> dict[str, Any]:
        """Return a value as a person reads it, with its path when it is a file.

        Args:
            value: One value of a record.

        Returns:
            The ``text`` to show, ``None`` when there is no value, and the
            ``path`` of a file inside the copy.
        """
        if isinstance(value, CopiedFile):
            return {"text": value.name, "path": value.path}
        if value is None or value == "":
            return {"text": None}
        if isinstance(value, datetime):
            return {"text": date_format(timezone.localtime(value), "DATETIME_FORMAT")}
        if isinstance(value, date):
            return {"text": date_format(value)}
        return {"text": value}
