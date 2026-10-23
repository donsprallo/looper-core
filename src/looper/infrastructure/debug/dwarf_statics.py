"""Reading what a build holds statically out of its debug information.

Every global and file scope static the compiler emitted is described
here with a type, and every type with a size. Following the one to the
other is the whole of it, plus the care any reader of a foreign file
needs: a type that points at itself, an entry that names no type, a
declaration that is not a definition.

A declaration without a location is skipped. It describes an object
that lives in another unit, and that unit describes it too; counting
both would count the bytes twice.
"""

from __future__ import annotations

from collections.abc import Iterator

from elftools.dwarf.compileunit import CompileUnit
from elftools.dwarf.die import DIE
from elftools.dwarf.dwarfinfo import DWARFInfo

from looper.domain.model.firmware import StaticSymbol
from looper.infrastructure.debug.dwarf_sources import file_table, source_of, text_of

VARIABLE_TAG = "DW_TAG_variable"
NAME_ATTRIBUTE = "DW_AT_name"
LOCATION_ATTRIBUTE = "DW_AT_location"
DECLARATION_ATTRIBUTE = "DW_AT_declaration"
TYPE_ATTRIBUTE = "DW_AT_type"
BYTE_SIZE_ATTRIBUTE = "DW_AT_byte_size"

CONSTANT_TAG = "DW_TAG_const_type"
ARRAY_TAG = "DW_TAG_array_type"
SUBRANGE_TAG = "DW_TAG_subrange_type"
COUNT_ATTRIBUTE = "DW_AT_count"
UPPER_BOUND_ATTRIBUTE = "DW_AT_upper_bound"

#: How far a type may point at another before this gives up. A typedef
#: of a typedef of an array of a structure is four; anything past this
#: is either generated or circular.
MAXIMUM_TYPE_DEPTH = 16


def read_statics(dwarf: DWARFInfo) -> tuple[StaticSymbol, ...]:
    """Every object the build holds statically, with its size."""
    found: list[StaticSymbol] = []
    for unit in dwarf.iter_CUs():
        found.extend(_statics_of(dwarf, unit))
    return tuple(found)


def _statics_of(dwarf: DWARFInfo, unit: CompileUnit) -> Iterator[StaticSymbol]:
    """Every object one compilation unit defines."""
    files = file_table(dwarf, unit)
    for die in unit.iter_DIEs():
        symbol = _symbol_of(die, files)
        if symbol is not None:
            yield symbol


def _symbol_of(die: DIE, files: tuple[object, ...]) -> StaticSymbol | None:
    """One object, when the entry describes one that takes up room."""
    if die.tag != VARIABLE_TAG:
        return None
    if (LOCATION_ATTRIBUTE not in die.attributes) or (DECLARATION_ATTRIBUTE in die.attributes):
        return None
    name = die.attributes.get(NAME_ATTRIBUTE)
    size = _size_of(die)
    if (name is None) or (size is None) or (size <= 0):
        return None
    return StaticSymbol(
        name=text_of(name.value),
        bytes_used=size,
        source=source_of(die, files),  # type: ignore[arg-type]
        is_constant=_is_constant(die),
    )


def _size_of(die: DIE | None) -> int | None:
    """How many bytes the object or type an entry describes takes up.

    Entries refer to types which refer to types: a variable names a
    typedef which names a const which names an array. The size is
    whichever link in that chain declares one, or the arithmetic of an
    array when the chain reaches one.
    """
    current: DIE | None = die
    for _ in range(MAXIMUM_TYPE_DEPTH):
        if current is None:
            return None
        declared = current.attributes.get(BYTE_SIZE_ATTRIBUTE)
        if declared is not None:
            return int(declared.value)
        if current.tag == ARRAY_TAG:
            return _array_size_of(current)
        current = _type_behind(current)
    return None


def _array_size_of(array: DIE) -> int | None:
    """How many bytes an array takes up.

    An array rarely carries a size of its own. It carries the type of
    its elements and one subrange entry per dimension, and the product
    of those is the answer. Reading only the element type -- which is
    what following the type chain does -- would report a buffer of
    sixty four thousand samples as one sample, and the objects that
    matter most to a memory budget are exactly the large arrays.
    """
    element = _size_of(_type_behind(array))
    if element is None:
        return None
    total = element
    dimensions = 0
    for child in array.iter_children():
        if child.tag != SUBRANGE_TAG:
            continue
        length = _dimension_of(child)
        if length is None:
            return None
        total *= length
        dimensions += 1
    return total if dimensions > 0 else None


def _dimension_of(subrange: DIE) -> int | None:
    """How many elements one dimension holds.

    Written as a count by some compilers and as the highest index by
    others, and as neither for an array of unknown length.
    """
    count = subrange.attributes.get(COUNT_ATTRIBUTE)
    if count is not None:
        return int(count.value)
    upper = subrange.attributes.get(UPPER_BOUND_ATTRIBUTE)
    if upper is None:
        return None
    return int(upper.value) + 1


def _is_constant(die: DIE) -> bool:
    """Whether the object is read only, and so flash rather than RAM."""
    current: DIE | None = _type_behind(die)
    for _ in range(MAXIMUM_TYPE_DEPTH):
        if current is None:
            return False
        if current.tag == CONSTANT_TAG:
            return True
        if BYTE_SIZE_ATTRIBUTE in current.attributes:
            return False
        current = _type_behind(current)
    return False


def _type_behind(die: DIE) -> DIE | None:
    """The type an entry refers to, or None when it names none."""
    if TYPE_ATTRIBUTE not in die.attributes:
        return None
    try:
        return die.get_DIE_from_attribute(TYPE_ATTRIBUTE)
    except (KeyError, AttributeError, ValueError):
        return None
