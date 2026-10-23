"""The run of bits a bit field occupies inside the bytes that hold it."""

from __future__ import annotations

from dataclasses import dataclass

BITS_PER_BYTE = 8
MAXIMUM_BIT_WIDTH = 64


@dataclass(frozen=True)
class BitRange:
    """Where a bit field sits within the bytes at its address.

    A bit field has no address of its own: it shares one with the bits around
    it. What it does have is a position, and that position is what a reader
    needs in order to shift and mask the surrounding bytes down to a value.

    The offset is counted from the least significant bit of the first byte at
    the address, which is how a little endian machine lays the bits out. The
    address a bit field is given is therefore the byte its first bit falls
    in, not the start of the structure that declares it.

    Attributes:
        offset: Bits to skip from the start of the addressed bytes.
        width: Bits the field occupies.
    """

    offset: int
    width: int

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("A bit field cannot start before its own address")
        if not 1 <= self.width <= MAXIMUM_BIT_WIDTH:
            raise ValueError(f"A bit field of {self.width} bits is not readable")

    @property
    def byte_width(self) -> int:
        """Bytes that have to be read to see every bit of the field."""
        return -(-(self.offset + self.width) // BITS_PER_BYTE)

    def fits_in(self, byte_width: int) -> bool:
        """Whether the field is contained in the given number of bytes."""
        return self.byte_width <= byte_width
