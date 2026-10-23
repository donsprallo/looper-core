"""Reading the functions out of a build's debug information.

A profile arrives as addresses. This is what turns them back into names
and, more importantly, into the source files they were compiled from --
the one fact that says which part of a simulation a function belongs to.

The path takes assembling. A compiler writes the file as an index into
the line program's own table, the directory as a second index into
another, and leaves what is still relative to be joined onto the unit's
compilation directory. All three are needed before two files in
directories of the same name can be told apart.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePath

from elftools.dwarf.compileunit import CompileUnit
from elftools.dwarf.die import DIE
from elftools.dwarf.dwarfinfo import DWARFInfo

from looper.domain.model.firmware import FunctionSymbol
from looper.infrastructure.debug.dwarf_sources import file_table, source_of, text_of

SUBPROGRAM_TAG = "DW_TAG_subprogram"
NAME_ATTRIBUTE = "DW_AT_name"
LOW_PC_ATTRIBUTE = "DW_AT_low_pc"
HIGH_PC_ATTRIBUTE = "DW_AT_high_pc"


def read_functions(dwarf: DWARFInfo) -> tuple[FunctionSymbol, ...]:
    """Every function the debug information places at an address.

    A declaration without an address is skipped: it describes a function
    that lives somewhere else, and the profile will meet that one where
    it was defined.
    """
    found: list[FunctionSymbol] = []
    for unit in dwarf.iter_CUs():
        found.extend(_functions_of(dwarf, unit))
    return tuple(found)


def _functions_of(dwarf: DWARFInfo, unit: CompileUnit) -> Iterator[FunctionSymbol]:
    """Every function one compilation unit defines."""
    files = file_table(dwarf, unit)
    for die in unit.iter_DIEs():
        symbol = _symbol_of(die, files)
        if symbol is not None:
            yield symbol


def _symbol_of(die: DIE, files: tuple[PurePath | None, ...]) -> FunctionSymbol | None:
    """One function, when the entry describes one that has an address."""
    if die.tag != SUBPROGRAM_TAG:
        return None
    address = die.attributes.get(LOW_PC_ATTRIBUTE)
    name = die.attributes.get(NAME_ATTRIBUTE)
    if (address is None) or (name is None) or (address.value <= 0):
        return None
    return FunctionSymbol(
        name=text_of(name.value),
        link_time_address=int(address.value),
        source=source_of(die, files),
        size_bytes=_extent_of(die, int(address.value)),
    )


def _extent_of(die: DIE, low: int) -> int:
    """How far a function reaches past where it begins.

    Written either as a length or as the address one past the end,
    depending on the compiler and the version of the format, and the
    two are told apart by which side of the beginning it falls on.
    """
    high = die.attributes.get(HIGH_PC_ATTRIBUTE)
    if high is None:
        return 0
    value = int(high.value)
    return value - low if value > low else value
