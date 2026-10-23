"""What a project declares it holds about a person, and how it is read.

A project lists dotted paths to ``PersonalData`` subclasses in
``MVP_COMPLIANCE_PERSONAL_DATA``. Each one is a kind of record the project
holds about a person. Reading a kind for one user gives a section.
"""

import os
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.db.models.fields.files import FieldFile
from django.utils.functional import Promise
from django.utils.module_loading import import_string

#: The text of a label or heading: a string, or a lazy one translated when read.
Text = str | Promise


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
    """

    key: str
    heading: Text
    columns: tuple[tuple[str, Text], ...]
    rows: tuple[tuple[Any, ...], ...]
    description: Text = ""
    single: bool = False
    template_name: str | None = None


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

    heading: Text = ""
    description: Text = ""
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
        records = self.get_queryset(user)
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
                for record in records
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
            return self.get_copied_file(record, value)
        if value is None or value == "":
            return None
        if field.choices:
            return getattr(record, f"get_{field.name}_display")()
        if field.is_relation:
            return str(value)
        return value

    def get_copied_file(
        self, record: models.Model, field_file: FieldFile
    ) -> CopiedFile | None:
        """Place a stored file inside the copy.

        Args:
            record: The row the file belongs to.
            field_file: The row's value for the file field.

        Returns:
            The file with its path in the copy, or ``None`` when the row has no file.
        """
        if not field_file:
            return None
        name = os.path.basename(str(field_file.name))
        return CopiedFile(
            path=f"files/{self.key}/{record.pk}/{name}",
            name=name,
            field_file=field_file,
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
