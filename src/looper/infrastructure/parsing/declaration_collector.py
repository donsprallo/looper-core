"""Collection of the declarations found in one translation unit."""

from __future__ import annotations

from clang.cindex import Cursor, CursorKind, StorageClass, TypeKind

from looper.domain.model.c_api import CEnum, CExternData, CFunction, CRecord
from looper.infrastructure.parsing.declaration_reader import (
    is_anonymous,
    read_enum,
    read_extern_data,
    read_function,
    read_record,
)

RECORD_DECLARATIONS = frozenset({CursorKind.STRUCT_DECL, CursorKind.UNION_DECL})


class DeclarationCollector:
    """Gathers declarations of one header, keeping the first name that wins.

    A ``typedef struct { ... } name_t;`` reaches the collector as two cursors.
    Both describe the same type, so entries are keyed by name and the first
    usable one is kept. Anonymous declarations are ignored until a typedef
    gives them a name.
    """

    def __init__(self) -> None:
        self._functions: dict[str, CFunction] = {}
        self._records: dict[str, CRecord] = {}
        self._enums: dict[str, CEnum] = {}
        self._extern_data: dict[str, CExternData] = {}

    def add(self, cursor: Cursor) -> None:
        """Collect one top level declaration, ignoring anything unsupported."""
        if cursor.kind is CursorKind.FUNCTION_DECL:
            self._add_function(cursor)
        elif cursor.kind is CursorKind.VAR_DECL:
            self._add_extern_data(cursor)
        elif cursor.kind is CursorKind.TYPEDEF_DECL:
            self._add_typedef(cursor)
        elif cursor.kind in RECORD_DECLARATIONS:
            self._add_record(cursor, cursor.spelling)
        elif cursor.kind is CursorKind.ENUM_DECL:
            self._add_enum(cursor, cursor.spelling)

    @property
    def functions(self) -> tuple[CFunction, ...]:
        """Collected functions in source order."""
        return tuple(self._functions.values())

    @property
    def records(self) -> tuple[CRecord, ...]:
        """Collected structs and unions in source order."""
        return tuple(self._records.values())

    @property
    def enums(self) -> tuple[CEnum, ...]:
        """Collected enumerations in source order."""
        return tuple(self._enums.values())

    @property
    def extern_data(self) -> tuple[CExternData, ...]:
        """Collected exported data symbols in source order."""
        return tuple(self._extern_data.values())

    def _add_function(self, cursor: Cursor) -> None:
        """Collect a public function, skipping internal linkage."""
        if cursor.storage_class is StorageClass.STATIC:
            return
        self._functions.setdefault(cursor.spelling, read_function(cursor))

    def _add_extern_data(self, cursor: Cursor) -> None:
        """Collect a data symbol the header exports for other modules."""
        if cursor.storage_class is not StorageClass.EXTERN:
            return
        self._extern_data.setdefault(cursor.spelling, read_extern_data(cursor))

    def _add_typedef(self, cursor: Cursor) -> None:
        """Collect the record or enumeration a typedef gives a name to."""
        underlying = cursor.underlying_typedef_type.get_canonical()
        declaration = underlying.get_declaration()
        if underlying.kind is TypeKind.RECORD:
            self._add_record(declaration, cursor.spelling)
        elif underlying.kind is TypeKind.ENUM:
            self._add_enum(declaration, cursor.spelling)

    def _add_record(self, cursor: Cursor, name: str) -> None:
        """Collect a named record declaration."""
        if is_anonymous(name):
            return
        self._records.setdefault(name, read_record(cursor, name))

    def _add_enum(self, cursor: Cursor, name: str) -> None:
        """Collect a named enumeration declaration."""
        if is_anonymous(name):
            return
        self._enums.setdefault(name, read_enum(cursor, name))
