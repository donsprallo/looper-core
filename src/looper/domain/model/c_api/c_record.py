"""Struct and union declarations used by an adapter API."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique

from looper.domain.model.c_api.c_type import CType
from looper.domain.model.c_api.validation import ensure_non_empty, ensure_unique_names


@unique
class RecordKind(Enum):
    """Whether a record aggregates or overlays its fields."""

    STRUCT = "struct"
    UNION = "union"


@dataclass(frozen=True)
class CField:
    """A single member of a record.

    Attributes:
        name: Member name as declared in the header.
        type: Declared member type.
    """

    name: str
    type: CType

    def __post_init__(self) -> None:
        ensure_non_empty(self.name, "A field name")


@dataclass(frozen=True)
class CRecord:
    """A struct or union that the generated simulation has to mirror.

    Attributes:
        name: Type name used by the adapter API.
        kind: Whether the record is a struct or a union.
        fields: Declared members in source order.
    """

    name: str
    kind: RecordKind = RecordKind.STRUCT
    fields: tuple[CField, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        ensure_non_empty(self.name, "A record name")
        ensure_unique_names(
            (member.name for member in self.fields),
            f"Record '{self.name}'",
        )

    @property
    def field_names(self) -> tuple[str, ...]:
        """Names of all declared members in source order."""
        return tuple(member.name for member in self.fields)
