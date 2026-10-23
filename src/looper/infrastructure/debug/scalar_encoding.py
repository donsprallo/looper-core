"""Translation from a DWARF base type to what the bytes mean."""

from __future__ import annotations

from looper.domain.model.firmware import VariableEncoding

DW_ATE_BOOLEAN = 0x02
DW_ATE_FLOAT = 0x04
DW_ATE_SIGNED = 0x05
DW_ATE_SIGNED_CHAR = 0x06
DW_ATE_UNSIGNED = 0x07
DW_ATE_UNSIGNED_CHAR = 0x08

# Base type encodings that name a number the trace can hold. The ones left
# out -- complex floats, decimal floats, packed decimals -- are scalars a
# client could in principle watch, but not ones a double represents
# faithfully. Addresses are left out for a different reason: see
# scalar_expansion for why a pointer is not offered.
ENCODINGS = {
    DW_ATE_BOOLEAN: VariableEncoding.BOOLEAN,
    DW_ATE_FLOAT: VariableEncoding.FLOATING_POINT,
    DW_ATE_SIGNED: VariableEncoding.SIGNED_INTEGER,
    DW_ATE_SIGNED_CHAR: VariableEncoding.SIGNED_INTEGER,
    DW_ATE_UNSIGNED: VariableEncoding.UNSIGNED_INTEGER,
    DW_ATE_UNSIGNED_CHAR: VariableEncoding.UNSIGNED_INTEGER,
}


def encoding_of(dwarf_encoding: int, byte_width: int) -> VariableEncoding | None:
    """Decide how to read a base type, if the trace can hold it at all.

    Args:
        dwarf_encoding: The ``DW_AT_encoding`` the base type carries.
        byte_width: Size of the type in bytes.

    Returns:
        The encoding, or ``None`` when the type is not one a client can watch,
        either because a double cannot represent it or because the compiler
        gave it a width the encoding has no form for -- a long double, say.
    """
    encoding = ENCODINGS.get(dwarf_encoding)
    if encoding is None:
        return None
    if not encoding.supports(byte_width):
        return None
    return encoding
