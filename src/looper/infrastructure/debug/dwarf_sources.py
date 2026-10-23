"""Which file a debug information entry was written in.

The path takes assembling. A compiler writes the file as an index into
the line program's own table, the directory as a second index into
another, and leaves what is still relative to be joined onto the unit's
compilation directory. All three are needed before two files in
directories of the same name can be told apart.

Shared by everything that asks where something came from: the functions
a profile measures and the objects a static memory report counts.
"""

from __future__ import annotations

from pathlib import PurePath

from elftools.dwarf.compileunit import CompileUnit
from elftools.dwarf.die import DIE
from elftools.dwarf.dwarfinfo import DWARFInfo

DECL_FILE_ATTRIBUTE = "DW_AT_decl_file"
COMPILATION_DIRECTORY_ATTRIBUTE = "DW_AT_comp_dir"


def source_of(die: DIE, files: tuple[PurePath | None, ...]) -> PurePath | None:
    """The file an entry was declared in, when the table knows it."""
    index = die.attributes.get(DECL_FILE_ATTRIBUTE)
    if index is None:
        return None
    position = int(index.value)
    if (position < 0) or (position >= len(files)):
        return None
    return files[position]


def file_table(dwarf: DWARFInfo, unit: CompileUnit) -> tuple[PurePath | None, ...]:
    """The unit's file table, resolved to whole paths."""
    program = dwarf.line_program_for_CU(unit)
    if program is None:
        return ()
    header = program.header
    directories = [text_of(entry) for entry in header.include_directory]
    root = _compilation_directory(unit)
    return tuple(_entry_path(entry, directories, root) for entry in header.file_entry)


def _entry_path(entry: object, directories: list[str], root: str) -> PurePath | None:
    """One file table entry as a path, absolute where anything says so."""
    name = text_of(getattr(entry, "name", b""))
    if not name:
        return None
    index = int(getattr(entry, "dir_index", 0))
    directory = directories[index] if 0 <= index < len(directories) else ""
    combined = PurePath(directory) / name if directory else PurePath(name)
    if combined.is_absolute() or not root:
        return combined
    return PurePath(root) / combined


def _compilation_directory(unit: CompileUnit) -> str:
    """Where the compiler was standing, which relative paths are against."""
    attribute = unit.get_top_DIE().attributes.get(COMPILATION_DIRECTORY_ATTRIBUTE)
    return text_of(attribute.value) if attribute is not None else ""


def text_of(value: object) -> str:
    """A DWARF string, which may arrive as bytes."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
