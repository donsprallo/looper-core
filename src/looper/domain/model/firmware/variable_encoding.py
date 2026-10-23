"""How the bytes of a firmware variable are to be read and written."""

from __future__ import annotations

import sys
from enum import Enum, unique

BITS_PER_BYTE = 8
INTEGER_BYTE_WIDTHS = (1, 2, 4, 8)
FLOAT_BYTE_WIDTHS = (4, 8)
BOOLEAN_BYTE_WIDTHS = (1,)

SINGLE_PRECISION_MAXIMUM = 3.4028234663852886e38
FLOAT_MAXIMUM = {4: SINGLE_PRECISION_MAXIMUM, 8: sys.float_info.max}


@unique
class VariableEncoding(Enum):
    """What the bytes at a variable's address mean.

    A watched variable is read as raw memory and reported as a double, which
    is the one numeric type the trace and the plot speak. The encoding is what
    turns those bytes into that number, and the number back into bytes when a
    client writes the variable.

    Pointers, structures and arrays have no encoding: they are not scalars, so
    they are paths on the way to one rather than something to watch.
    """

    SIGNED_INTEGER = "signed"
    UNSIGNED_INTEGER = "unsigned"
    FLOATING_POINT = "float"
    BOOLEAN = "bool"

    @property
    def supported_byte_widths(self) -> tuple[int, ...]:
        """Widths a value of this encoding may occupy."""
        if self is VariableEncoding.FLOATING_POINT:
            return FLOAT_BYTE_WIDTHS
        if self is VariableEncoding.BOOLEAN:
            return BOOLEAN_BYTE_WIDTHS
        return INTEGER_BYTE_WIDTHS

    @property
    def is_integral(self) -> bool:
        """Whether values of this encoding are whole numbers.

        A client editing such a variable should offer whole numbers only. A
        fractional value written to one is truncated towards zero, which is
        what the C assignment it stands in for would do.
        """
        return self is not VariableEncoding.FLOATING_POINT

    def supports(self, byte_width: int) -> bool:
        """Whether a value of this encoding can occupy the given width."""
        return byte_width in self.supported_byte_widths

    def value_range(self, byte_width: int) -> tuple[float, float]:
        """Lowest and highest value this encoding holds at the given width.

        Args:
            byte_width: Width of the value in bytes.

        Returns:
            The inclusive bounds.

        Raises:
            ValueError: If the encoding has no form of that width.
        """
        if not self.supports(byte_width):
            raise ValueError(f"A {self.value} variable has no {byte_width} byte form")
        if self is VariableEncoding.FLOATING_POINT:
            return (-FLOAT_MAXIMUM[byte_width], FLOAT_MAXIMUM[byte_width])
        return self.bit_value_range(byte_width * BITS_PER_BYTE)

    def bit_value_range(self, bit_width: int) -> tuple[float, float]:
        """Lowest and highest value this encoding holds in a run of bits.

        A bit field is not a whole number of bytes wide, so its range follows
        from how many bits it was declared with. A three bit signed field
        holds -4 to 3, and refusing 4 is the only honest answer: storing it
        would silently come back as -4.

        Args:
            bit_width: Width of the value in bits.

        Returns:
            The inclusive bounds.

        Raises:
            ValueError: If the encoding has no form made of bits.
        """
        if self is VariableEncoding.FLOATING_POINT:
            raise ValueError("A float has no bit field form")
        if self is VariableEncoding.BOOLEAN:
            return (0.0, 1.0)
        if self is VariableEncoding.UNSIGNED_INTEGER:
            return (0.0, float(2**bit_width - 1))
        magnitude = 2 ** (bit_width - 1)
        return (float(-magnitude), float(magnitude - 1))

    def accepts(self, value: float, byte_width: int) -> bool:
        """Whether the value fits the range this encoding holds at that width.

        Args:
            value: Value a client wants to write.
            byte_width: Width of the variable in bytes.

        Returns:
            Whether writing it would stay within range.

        Raises:
            ValueError: If the encoding has no form of that width.
        """
        minimum, maximum = self.value_range(byte_width)
        return minimum <= value <= maximum
