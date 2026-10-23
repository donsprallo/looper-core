"""Debug sections of a Windows executable.

A PE section header has eight bytes for a name. Every DWARF section name is
longer than that, so the linker stores the name in the COFF string table and
leaves a ``/offset`` reference behind. Resolving those references is the only
thing that makes a PE different from an ELF here: what is inside the sections
is the same DWARF either way.
"""

from __future__ import annotations

import io

import pefile
from elftools.dwarf.dwarfinfo import DebugSectionDescriptor

from looper.infrastructure.debug.errors import DebugInformationError

SYMBOL_ENTRY_SIZE = 18
LONG_NAME_PREFIX = "/"
DEBUG_SECTION_PREFIX = ".debug_"
PE32_PLUS_MAGIC = 0x20B
NAME_ENCODING = "ascii"


def pe_debug_sections(data: bytes) -> dict[str, DebugSectionDescriptor]:
    """Collect the DWARF sections of a Windows executable.

    Args:
        data: Whole executable.

    Returns:
        Each DWARF section by name, carrying its own stream.

    Raises:
        DebugInformationError: If the file cannot be read as a PE image.
    """
    image = _parse(data)
    string_table = _string_table_offset(image)
    sections = {}
    for section in image.sections:
        name = _section_name(section, data, string_table)
        if name.startswith(DEBUG_SECTION_PREFIX):
            sections[name] = _descriptor(section, data, name, image)
    return sections


def pe_address_size(data: bytes) -> int:
    """Pointer width of a Windows executable, in bytes."""
    image = _parse(data)
    return 8 if image.OPTIONAL_HEADER.Magic == PE32_PLUS_MAGIC else 4


def pe_link_time_base(data: bytes) -> int:
    """Base address a Windows executable was linked against.

    Read from the file rather than from the loaded image: a relocating loader
    overwrites this field in memory with the address it actually used.
    """
    image = _parse(data)
    return int(image.OPTIONAL_HEADER.ImageBase)


def _parse(data: bytes) -> pefile.PE:
    """Read the headers of a PE image.

    Raises:
        DebugInformationError: If the file is not a PE image.
    """
    try:
        return pefile.PE(data=data, fast_load=True)
    except pefile.PEFormatError as error:
        raise DebugInformationError(f"Not a readable Windows executable: {error}") from error


def _string_table_offset(image: pefile.PE) -> int:
    """Offset of the COFF string table, which follows the symbol table."""
    header = image.FILE_HEADER
    return int(header.PointerToSymbolTable) + int(header.NumberOfSymbols) * SYMBOL_ENTRY_SIZE


def _section_name(section: pefile.SectionStructure, data: bytes, string_table: int) -> str:
    """Resolve a section name, following a reference into the string table."""
    raw: bytes = section.Name
    stored = raw.rstrip(b"\x00").decode(NAME_ENCODING, errors="replace")
    if not stored.startswith(LONG_NAME_PREFIX) or not stored[1:].isdigit():
        return stored
    start = string_table + int(stored[1:])
    end = data.find(b"\x00", start)
    if not 0 <= start <= end:
        return stored
    return data[start:end].decode(NAME_ENCODING, errors="replace")


def _descriptor(
    section: pefile.SectionStructure, data: bytes, name: str, image: pefile.PE
) -> DebugSectionDescriptor:
    """Describe one section so that the DWARF parser can read it.

    The section gets a stream of its own starting at offset zero, which is why
    the global offset is zero rather than the position in the file.
    """
    start = int(section.PointerToRawData)
    stored = int(section.SizeOfRawData)
    size = min(stored, int(section.Misc_VirtualSize) or stored)
    return DebugSectionDescriptor(
        stream=io.BytesIO(data[start : start + size]),
        name=name,
        global_offset=0,
        size=size,
        address=int(image.OPTIONAL_HEADER.ImageBase) + int(section.VirtualAddress),
    )
