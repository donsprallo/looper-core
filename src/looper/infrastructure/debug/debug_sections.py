"""Opening the debug information of a built simulation.

A simulation is an ordinary host executable, so its container is whatever the
host uses: ELF on Linux, PE on Windows. The DWARF inside is the same, and this
module is where the difference between the two containers ends.
"""

from __future__ import annotations

import io
from pathlib import Path

from elftools.dwarf.dwarfinfo import DebugSectionDescriptor, DwarfConfig, DWARFInfo
from elftools.elf.elffile import ELFFile

from looper.infrastructure.debug.errors import DebugInformationError
from looper.infrastructure.debug.pe_debug_sections import (
    pe_address_size,
    pe_debug_sections,
    pe_link_time_base,
)

ELF_MAGIC = b"\x7fELF"
PE_MAGIC = b"MZ"

REQUIRED_SECTION = ".debug_info"

ADDRESS_SIZE_ARCHITECTURE = {4: "x86", 8: "x64"}

# Every section DWARFInfo wants, by the keyword it wants it under. Sections
# the executable does not carry are passed as None, which is what pyelftools
# expects for debug information that simply is not there.
SECTION_PARAMETERS = {
    "debug_info_sec": ".debug_info",
    "debug_aranges_sec": ".debug_aranges",
    "debug_abbrev_sec": ".debug_abbrev",
    "debug_frame_sec": ".debug_frame",
    "eh_frame_sec": ".eh_frame",
    "debug_str_sec": ".debug_str",
    "debug_loc_sec": ".debug_loc",
    "debug_ranges_sec": ".debug_ranges",
    "debug_line_sec": ".debug_line",
    "debug_pubtypes_sec": ".debug_pubtypes",
    "debug_pubnames_sec": ".debug_pubnames",
    "debug_addr_sec": ".debug_addr",
    "debug_str_offsets_sec": ".debug_str_offsets",
    "debug_line_str_sec": ".debug_line_str",
    "debug_loclists_sec": ".debug_loclists",
    "debug_rnglists_sec": ".debug_rnglists",
    "debug_sup_sec": ".debug_sup",
    "gnu_debugaltlink_sec": ".gnu_debugaltlink",
    "debug_types_sec": ".debug_types",
}


def open_dwarf_info(executable: Path) -> DWARFInfo:
    """Read the DWARF information a built simulation carries.

    Args:
        executable: Simulation built with debug information.

    Returns:
        The debug information, ready to be walked.

    Raises:
        FileNotFoundError: If the executable does not exist.
        DebugInformationError: If the container is unknown or carries no DWARF.
    """
    data = executable.read_bytes()
    if data.startswith(ELF_MAGIC):
        return _elf_dwarf_info(data, executable)
    if data.startswith(PE_MAGIC):
        return _dwarf_info(pe_debug_sections(data), pe_address_size(data), executable)
    raise DebugInformationError(f"{executable} is neither an ELF nor a Windows executable")


def _elf_dwarf_info(data: bytes, executable: Path) -> DWARFInfo:
    """Read the DWARF information of an ELF executable.

    Raises:
        DebugInformationError: If the executable carries none.
    """
    elf = ELFFile(io.BytesIO(data))
    if not elf.has_dwarf_info():
        raise DebugInformationError(_no_debug_information(executable))
    return elf.get_dwarf_info()


def _dwarf_info(
    sections: dict[str, DebugSectionDescriptor], address_size: int, executable: Path
) -> DWARFInfo:
    """Assemble the debug information from sections read out of a container.

    Raises:
        DebugInformationError: If the sections carry no compilation units.
    """
    if REQUIRED_SECTION not in sections:
        raise DebugInformationError(_no_debug_information(executable))
    config = DwarfConfig(
        little_endian=True,
        default_address_size=address_size,
        machine_arch=ADDRESS_SIZE_ARCHITECTURE[address_size],
    )
    found = {keyword: sections.get(name) for keyword, name in SECTION_PARAMETERS.items()}
    return DWARFInfo(config=config, **found)


def _no_debug_information(executable: Path) -> str:
    """Explain what is missing and how to get it."""
    return (
        f"{executable} carries no debug information. Build the simulation with "
        '-g, for example warnings = ["-Wall", "-g"] in looper.toml.'
    )


def read_link_time_base(executable: Path) -> int:
    """Read the base address an executable was linked against.

    The debug information names addresses relative to this base. It has to
    come from the file: a process asking its own loaded headers would get the
    address the loader actually used instead.

    Args:
        executable: Simulation built with debug information.

    Returns:
        The base address. Zero for a position independent executable, which
        is linked against no base at all.

    Raises:
        FileNotFoundError: If the executable does not exist.
        DebugInformationError: If the container is unknown.
    """
    data = executable.read_bytes()
    if data.startswith(ELF_MAGIC):
        return _elf_link_time_base(data)
    if data.startswith(PE_MAGIC):
        return pe_link_time_base(data)
    raise DebugInformationError(f"{executable} is neither an ELF nor a Windows executable")


def _elf_link_time_base(data: bytes) -> int:
    """Lowest address the loadable segments of an ELF executable span."""
    elf = ELFFile(io.BytesIO(data))
    addresses = [
        int(segment["p_vaddr"]) for segment in elf.iter_segments() if segment["p_type"] == "PT_LOAD"
    ]
    return min(addresses, default=0)
