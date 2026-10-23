"""Reading the parts of a DWARF type entry that locating a scalar needs.

A type is described by a chain of entries: a typedef pointing at a qualifier
pointing at a structure whose members point at types of their own. Walking
that chain is mechanical and says nothing about what a watch is, so it lives
apart from the walk that uses it.
"""

from __future__ import annotations

from dataclasses import dataclass

from elftools.dwarf.die import DIE

TYPE_ATTRIBUTE = "DW_AT_type"
NAME_ATTRIBUTE = "DW_AT_name"
BYTE_SIZE_ATTRIBUTE = "DW_AT_byte_size"
MEMBER_OFFSET_ATTRIBUTE = "DW_AT_data_member_location"
BIT_SIZE_ATTRIBUTE = "DW_AT_bit_size"
DATA_BIT_OFFSET_ATTRIBUTE = "DW_AT_data_bit_offset"
BIT_OFFSET_ATTRIBUTE = "DW_AT_bit_offset"
BITS_PER_BYTE = 8
ENCODING_ATTRIBUTE = "DW_AT_encoding"
COUNT_ATTRIBUTE = "DW_AT_count"
UPPER_BOUND_ATTRIBUTE = "DW_AT_upper_bound"

CONSTANT_TAG = "DW_TAG_const_type"
TRANSPARENT_TAGS = frozenset(
    {CONSTANT_TAG, "DW_TAG_typedef", "DW_TAG_volatile_type", "DW_TAG_restrict_type"}
)
AGGREGATE_TAGS = frozenset({"DW_TAG_structure_type", "DW_TAG_union_type", "DW_TAG_class_type"})
MEMBER_TAG = "DW_TAG_member"
ARRAY_TAG = "DW_TAG_array_type"
BASE_TAG = "DW_TAG_base_type"
ENUMERATION_TAG = "DW_TAG_enumeration_type"
SUBRANGE_TAG = "DW_TAG_subrange_type"


@dataclass(frozen=True)
class ResolvedType:
    """A type with its typedefs and qualifiers removed.

    Attributes:
        die: The type itself, or ``None`` for void.
        is_constant: Whether a qualifier on the way declared it read only.
    """

    die: DIE | None
    is_constant: bool


def resolve(type_die: DIE | None, is_constant: bool = False) -> ResolvedType:
    """Strip typedefs and qualifiers, remembering whether one was const."""
    current = type_die
    constant = is_constant
    while current is not None and current.tag in TRANSPARENT_TAGS:
        constant = constant or current.tag == CONSTANT_TAG
        current = attribute_die(current, TYPE_ATTRIBUTE)
    return ResolvedType(die=current, is_constant=constant)


def attribute_die(die: DIE, attribute: str) -> DIE | None:
    """Follow a reference attribute, if the entry carries one."""
    if attribute not in die.attributes:
        return None
    return die.get_DIE_from_attribute(attribute)


def member_name(member: DIE) -> str | None:
    """Name of a member, or ``None`` for an anonymous structure or union."""
    name = member.attributes.get(NAME_ATTRIBUTE)
    if name is None:
        return None
    return text_of(name.value)


def member_offset(member: DIE) -> int | None:
    """Byte offset of a member, or ``None`` when it is not a plain constant."""
    offset = member.attributes.get(MEMBER_OFFSET_ATTRIBUTE)
    if offset is None:
        return 0
    if isinstance(offset.value, int):
        return offset.value
    return None


def is_bit_field(member: DIE) -> bool:
    """Whether a member occupies a run of bits rather than whole bytes."""
    return BIT_SIZE_ATTRIBUTE in member.attributes


def bit_placement(member: DIE, storage_bytes: int) -> tuple[int, int] | None:
    """Where a bit field sits, as bits from the start of its structure.

    Two spellings exist. Since DWARF 4 a member carries the offset of its
    first bit outright. Before that it carried the offset counted from the
    most significant end of the storage unit, which has to be turned around
    to mean the same thing on a little endian machine.

    Args:
        member: The member entry.
        storage_bytes: Size of the unit the older spelling counts within.

    Returns:
        The first bit and the width, or ``None`` when neither spelling is
        complete enough to locate the field.
    """
    width = member.attributes.get(BIT_SIZE_ATTRIBUTE)
    if width is None or not isinstance(width.value, int):
        return None
    modern = member.attributes.get(DATA_BIT_OFFSET_ATTRIBUTE)
    if modern is not None and isinstance(modern.value, int):
        return modern.value, width.value
    legacy = member.attributes.get(BIT_OFFSET_ATTRIBUTE)
    if legacy is None or not isinstance(legacy.value, int) or storage_bytes <= 0:
        return None
    from_the_top = storage_bytes * BITS_PER_BYTE - legacy.value - width.value
    byte_offset = member_offset(member) or 0
    return byte_offset * BITS_PER_BYTE + from_the_top, width.value


def element_count(array: DIE) -> int | None:
    """Number of elements an array holds, or ``None`` when it is unbounded."""
    for child in array.iter_children():
        if child.tag != SUBRANGE_TAG:
            continue
        count = child.attributes.get(COUNT_ATTRIBUTE)
        if count is not None and isinstance(count.value, int):
            return count.value
        upper = child.attributes.get(UPPER_BOUND_ATTRIBUTE)
        if upper is not None and isinstance(upper.value, int):
            return upper.value + 1
    return None


def byte_size(type_die: DIE | None) -> int | None:
    """Size of a type in bytes, looking through typedefs and qualifiers."""
    resolved = resolve(type_die).die
    if resolved is None:
        return None
    size = resolved.attributes.get(BYTE_SIZE_ATTRIBUTE)
    if size is not None and isinstance(size.value, int):
        return size.value
    if resolved.tag != ARRAY_TAG:
        return None
    return _array_byte_size(resolved)


def _array_byte_size(array: DIE) -> int | None:
    """Size of an array the compiler did not give an explicit size."""
    stride = byte_size(attribute_die(array, TYPE_ATTRIBUTE))
    count = element_count(array)
    if stride is None or count is None:
        return None
    return stride * count


def text_of(value: bytes | str) -> str:
    """Read a DWARF string attribute, whichever form it came in."""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
