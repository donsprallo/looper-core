"""Adapter surface repository backed by libclang."""

from __future__ import annotations

from pathlib import Path

from clang.cindex import Cursor, Diagnostic, Index, TranslationUnit

from looper.domain.model.c_api import AdapterModule, AdapterSurface
from looper.domain.repositories import AdapterSurfaceRepository
from looper.domain.services import module_name_from_header
from looper.infrastructure.parsing.clang_library import create_index
from looper.infrastructure.parsing.declaration_collector import DeclarationCollector
from looper.infrastructure.parsing.errors import HeaderParseError
from looper.infrastructure.parsing.parse_options import ParseOptions

HEADER_PATTERN = "*.h"
BLOCKING_SEVERITIES = frozenset({Diagnostic.Error, Diagnostic.Fatal})


class LibclangAdapterSurfaceRepository(AdapterSurfaceRepository):
    """Reads adapter declarations by running the libclang front end.

    Every header in the directory is parsed on its own, in file name order, so
    that a module always corresponds to exactly one header.
    """

    def __init__(self, options: ParseOptions | None = None) -> None:
        self._options = options if options is not None else ParseOptions()
        self._index: Index | None = None

    def load(self, header_directory: Path) -> AdapterSurface:
        """Parse every header in the directory into one adapter surface.

        Raises:
            FileNotFoundError: If the directory does not exist.
            HeaderParseError: If a header reports a compiler error.
        """
        if not header_directory.is_dir():
            raise FileNotFoundError(f"'{header_directory}' is not a directory")
        headers = sorted(header_directory.glob(HEADER_PATTERN))
        return AdapterSurface(modules=tuple(self._read_module(header) for header in headers))

    def _read_module(self, header_path: Path) -> AdapterModule:
        """Translate a single header into a module."""
        translation_unit = self._parse(header_path)
        collector = DeclarationCollector()
        for cursor in translation_unit.cursor.get_children():
            if _is_declared_in(cursor, header_path):
                collector.add(cursor)
        return AdapterModule(
            name=module_name_from_header(header_path),
            header_path=header_path,
            functions=collector.functions,
            records=collector.records,
            enums=collector.enums,
            extern_data=collector.extern_data,
        )

    def _parse(self, header_path: Path) -> TranslationUnit:
        """Run the front end over one header and reject compiler errors."""
        if self._index is None:
            self._index = create_index()
        translation_unit = self._index.parse(str(header_path), args=self._options.clang_arguments())
        blocking = _blocking_diagnostics(translation_unit)
        if blocking:
            raise HeaderParseError(str(header_path), blocking)
        return translation_unit


def _blocking_diagnostics(translation_unit: TranslationUnit) -> tuple[str, ...]:
    """Collect the diagnostics that make a translation unit unusable."""
    return tuple(
        f"{diagnostic.location}: {diagnostic.spelling}"
        for diagnostic in translation_unit.diagnostics
        if diagnostic.severity in BLOCKING_SEVERITIES
    )


def _is_declared_in(cursor: Cursor, header_path: Path) -> bool:
    """Report whether a cursor originates from the header itself."""
    location = cursor.location.file
    if location is None:
        return False
    return Path(location.name).resolve() == header_path.resolve()
