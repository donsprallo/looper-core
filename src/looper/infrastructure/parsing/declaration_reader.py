"""Translation of individual libclang cursors into domain declarations."""

from __future__ import annotations

from collections.abc import Iterator

from clang.cindex import Cursor, CursorKind

from looper.domain.model.c_api import (
    CEnum,
    CEnumerator,
    CExternData,
    CField,
    CFunction,
    CParameter,
    CRecord,
    RecordKind,
)
from looper.infrastructure.parsing.type_mapper import map_type

ANONYMOUS_MARKER = "(unnamed"
PLACEHOLDER_PARAMETER_PREFIX = "argument"


def is_anonymous(spelling: str) -> bool:
    """Report whether a declaration carries no usable name.

    libclang spells an unnamed record as ``struct (unnamed at <file>:<line>)``,
    which is a source location rather than a name a generator could emit.
    """
    return not spelling or ANONYMOUS_MARKER in spelling


def read_function(cursor: Cursor) -> CFunction:
    """Read a function declaration with its parameters and doc comment."""
    return CFunction(
        name=cursor.spelling,
        return_type=map_type(cursor.result_type),
        parameters=tuple(_read_parameters(cursor)),
        documentation=cursor.raw_comment,
    )


def read_record(cursor: Cursor, name: str) -> CRecord:
    """Read a struct or union declaration under the given name.

    Unnamed members are skipped: generated code addresses members by name, so
    a member without one carries nothing the generator could use.
    """
    return CRecord(
        name=name,
        kind=_record_kind(cursor),
        fields=tuple(
            CField(name=member.spelling, type=map_type(member.type))
            for member in cursor.type.get_fields()
            if not is_anonymous(member.spelling)
        ),
    )


def read_enum(cursor: Cursor, name: str) -> CEnum:
    """Read an enumeration declaration under the given name."""
    return CEnum(
        name=name,
        enumerators=tuple(
            CEnumerator(name=child.spelling, value=child.enum_value)
            for child in cursor.get_children()
            if child.kind is CursorKind.ENUM_CONSTANT_DECL
        ),
    )


def read_extern_data(cursor: Cursor) -> CExternData:
    """Read an exported data symbol such as an interface table."""
    return CExternData(name=cursor.spelling, type=map_type(cursor.type))


def _record_kind(cursor: Cursor) -> RecordKind:
    """Classify a record declaration as a struct or a union."""
    if cursor.kind is CursorKind.UNION_DECL:
        return RecordKind.UNION
    return RecordKind.STRUCT


def _read_parameters(cursor: Cursor) -> Iterator[CParameter]:
    """Read the parameters of a function, naming unnamed ones by position."""
    for index, argument in enumerate(cursor.get_arguments()):
        name = argument.spelling or f"{PLACEHOLDER_PARAMETER_PREFIX}{index}"
        yield CParameter(name=name, type=map_type(argument.type))
