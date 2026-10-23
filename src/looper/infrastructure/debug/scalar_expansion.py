"""Walking a DWARF type down to the scalars a client can watch.

A firmware keeps most of its state in structures. ``g_app_config`` is not a
number, but somewhere inside it is one, and that is what a client wants to
plot. This module walks a type until it reaches scalars, carrying the address
along so that each one comes out knowing where it lives.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from elftools.dwarf.die import DIE

from looper.domain.model.firmware import (
    BitRange,
    FirmwareVariable,
    VariableEncoding,
    VariablePath,
)
from looper.infrastructure.debug.dwarf_types import (
    AGGREGATE_TAGS,
    ARRAY_TAG,
    BASE_TAG,
    ENCODING_ATTRIBUTE,
    ENUMERATION_TAG,
    MEMBER_TAG,
    TYPE_ATTRIBUTE,
    ResolvedType,
    attribute_die,
    bit_placement,
    byte_size,
    element_count,
    is_bit_field,
    member_name,
    member_offset,
    resolve,
)
from looper.infrastructure.debug.scalar_encoding import encoding_of

ENUMERATION_ENCODING = VariableEncoding.SIGNED_INTEGER
BITS_PER_BYTE = 8


@dataclass(frozen=True)
class ExpansionLimits:
    """How far into a type the walk goes before it stops.

    A firmware's configuration structure can expand into more scalars than a
    client can usefully show, and a large array expands into near copies of
    the same entry. Stopping is better than an unusable list; the limits are
    here rather than hard coded so that a caller who wants the whole thing can
    ask for it.

    Attributes:
        maximum_depth: Nesting levels of structures and arrays to follow.
        maximum_array_elements: Elements of one array to expand.
    """

    maximum_depth: int = 8
    maximum_array_elements: int = 32


class ScalarExpander:
    """Produces every watchable scalar inside a type."""

    def __init__(self, limits: ExpansionLimits | None = None) -> None:
        self._limits = limits if limits is not None else ExpansionLimits()

    def expand(
        self,
        type_die: DIE | None,
        path: str,
        address: int,
        is_constant: bool = False,
        depth: int = 0,
    ) -> Iterator[FirmwareVariable]:
        """Yield every scalar the type contains, with its own address.

        Args:
            type_die: Type to walk, already a type rather than a declaration.
            path: Path the caller reached this type by.
            address: Link time address the type sits at.
            is_constant: Whether an enclosing qualifier made it read only.
            depth: Nesting level reached so far.

        Yields:
            One variable per scalar, in declaration order.
        """
        if depth > self._limits.maximum_depth:
            return
        resolved = resolve(type_die, is_constant)
        if resolved.die is None:
            return
        yield from self._dispatch(resolved, path, address, depth)

    def _dispatch(
        self, resolved: ResolvedType, path: str, address: int, depth: int
    ) -> Iterator[FirmwareVariable]:
        """Send a resolved type to the walk its tag calls for."""
        tag = resolved.die.tag if resolved.die is not None else None
        if tag in AGGREGATE_TAGS:
            yield from self._expand_members(resolved, path, address, depth)
            return
        if tag == ARRAY_TAG:
            yield from self._expand_elements(resolved, path, address, depth)
            return
        scalar = _scalar(resolved, path, address)
        if scalar is not None:
            yield scalar

    def _expand_members(
        self, resolved: ResolvedType, path: str, address: int, depth: int
    ) -> Iterator[FirmwareVariable]:
        """Walk every member of a structure or union."""
        assert resolved.die is not None
        storage_bytes = byte_size(resolved.die) or 0
        for member in resolved.die.iter_children():
            if member.tag != MEMBER_TAG:
                continue
            if is_bit_field(member):
                field = _bit_field(member, resolved, path, address, storage_bytes)
                if field is not None:
                    yield field
                continue
            offset = member_offset(member)
            if offset is None:
                continue
            yield from self.expand(
                attribute_die(member, TYPE_ATTRIBUTE),
                _member_path(path, member),
                address + offset,
                resolved.is_constant,
                depth + 1,
            )

    def _expand_elements(
        self, resolved: ResolvedType, path: str, address: int, depth: int
    ) -> Iterator[FirmwareVariable]:
        """Walk the elements of an array, up to the limit."""
        assert resolved.die is not None
        element = attribute_die(resolved.die, TYPE_ATTRIBUTE)
        stride = byte_size(element)
        count = element_count(resolved.die)
        if element is None or stride is None or count is None:
            return
        for index in range(min(count, self._limits.maximum_array_elements)):
            yield from self.expand(
                element,
                f"{path}[{index}]",
                address + index * stride,
                resolved.is_constant,
                depth + 1,
            )


def _scalar(resolved: ResolvedType, path: str, address: int) -> FirmwareVariable | None:
    """Describe a type as a watchable scalar, or report that it is not one."""
    assert resolved.die is not None
    byte_width = byte_size(resolved.die)
    if byte_width is None:
        return None
    encoding = _scalar_encoding(resolved.die, byte_width)
    if encoding is None:
        return None
    return FirmwareVariable(
        path=VariablePath(path),
        link_time_address=address,
        encoding=encoding,
        byte_width=byte_width,
        is_constant=resolved.is_constant,
    )


def _bit_field(
    member: DIE, enclosing: ResolvedType, path: str, address: int, storage_bytes: int
) -> FirmwareVariable | None:
    """Describe one bit field as a value with an address and a bit range.

    A bit field is given the byte its first bit falls in, and an offset
    within that byte. Addressing it from the start of the structure instead
    would mean reading the whole structure to see three bits of it.
    """
    placement = bit_placement(member, storage_bytes)
    encoding = _bit_field_encoding(member)
    if placement is None or encoding is None:
        return None
    first_bit, width = placement
    bits = BitRange(offset=first_bit % BITS_PER_BYTE, width=width)
    return FirmwareVariable(
        path=VariablePath(_member_path(path, member)),
        link_time_address=address + first_bit // BITS_PER_BYTE,
        encoding=encoding,
        byte_width=bits.byte_width,
        is_constant=enclosing.is_constant,
        bits=bits,
    )


def _bit_field_encoding(member: DIE) -> VariableEncoding | None:
    """Decide how to read a bit field, which is never a floating point one."""
    declared = resolve(attribute_die(member, TYPE_ATTRIBUTE)).die
    if declared is None:
        return None
    if declared.tag == ENUMERATION_TAG:
        return ENUMERATION_ENCODING
    if declared.tag != BASE_TAG:
        return None
    dwarf_encoding = declared.attributes.get(ENCODING_ATTRIBUTE)
    if dwarf_encoding is None:
        return None
    encoding = encoding_of(int(dwarf_encoding.value), byte_size(declared) or 1)
    return None if encoding is VariableEncoding.FLOATING_POINT else encoding


def _scalar_encoding(type_die: DIE, byte_width: int) -> VariableEncoding | None:
    """Decide how to read a leaf type, or report that it is not a leaf.

    A pointer is deliberately not a leaf. Its value is an address, and an
    address is about where the firmware put something rather than about
    what the firmware is doing; plotted, it is noise. Showing what it points
    at instead is a different and much harder question -- a ``void *`` has
    no target type to show, a function pointer has nothing to read, and any
    pointer may be stale -- so this reports neither rather than one badly.
    """
    if type_die.tag == ENUMERATION_TAG:
        return ENUMERATION_ENCODING if ENUMERATION_ENCODING.supports(byte_width) else None
    if type_die.tag != BASE_TAG:
        return None
    dwarf_encoding = type_die.attributes.get(ENCODING_ATTRIBUTE)
    if dwarf_encoding is None:
        return None
    return encoding_of(int(dwarf_encoding.value), byte_width)


def _member_path(path: str, member: DIE) -> str:
    """Name a member, keeping the enclosing path for an anonymous one."""
    name = member_name(member)
    if name is None:
        return path
    return f"{path}.{name}"
