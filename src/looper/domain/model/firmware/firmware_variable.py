"""A scalar in the firmware's memory, as the debug information describes it."""

from __future__ import annotations

from dataclasses import dataclass, field

from looper.domain.model.firmware.bit_range import BitRange
from looper.domain.model.firmware.variable_encoding import VariableEncoding
from looper.domain.model.firmware.variable_origin import VariableOrigin
from looper.domain.model.firmware.variable_path import VariablePath


@dataclass(frozen=True)
class FirmwareVariable:
    """One scalar a client can watch, and usually write.

    Only variables with static storage are reachable this way. A local lives
    on a stack frame that exists while its function runs, so it has no address
    that stays meaningful between one firmware loop iteration and the next.

    The declaring file is excluded from comparison: two descriptions of the
    same address with the same encoding name the same variable, whichever
    translation unit the debug information attributed it to.

    Attributes:
        path: Where the scalar sits, and how a client names it.
        link_time_address: Address the debug information gives. The running
            process may have been relocated, so this is not yet an address to
            read; see :class:`LoadedImage`.
        encoding: What the bytes at that address mean.
        byte_width: How many bytes the scalar occupies.
        is_constant: Whether the firmware declared it read only.
        bits: The run of bits the value occupies, for a bit field. ``None``
            when the value is the whole of the bytes at its address.
        origin: Whether the variable is the firmware's or the simulation's.
            Excluded from comparison for the same reason the declaring file
            is: it follows from which unit described the address, and the
            address is what says which variable this is.
        declared_in: Source file the debug information attributes it to.
    """

    path: VariablePath
    link_time_address: int
    encoding: VariableEncoding
    byte_width: int
    is_constant: bool = False
    bits: BitRange | None = None
    origin: VariableOrigin = field(default=VariableOrigin.FIRMWARE, compare=False)
    declared_in: str | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if self.link_time_address <= 0:
            raise ValueError(f"Variable '{self.path}' has no usable address")
        if self.bits is not None:
            self._check_bit_field()
            return
        if not self.encoding.supports(self.byte_width):
            raise ValueError(
                f"Variable '{self.path}' is {self.byte_width} bytes, "
                f"which is not a {self.encoding.value} width"
            )

    def _check_bit_field(self) -> None:
        """Reject a bit field the bytes at the address do not contain.

        Raises:
            ValueError: If the field does not fit, or has no bit form.
        """
        assert self.bits is not None
        if self.encoding is VariableEncoding.FLOATING_POINT:
            raise ValueError(f"Variable '{self.path}' is a float, which has no bit field form")
        if not self.bits.fits_in(self.byte_width):
            raise ValueError(
                f"Variable '{self.path}' needs {self.bits.byte_width} bytes "
                f"to reach its bits, not {self.byte_width}"
            )

    @property
    def display_name(self) -> str:
        """Full path, which is what a client shows and searches on."""
        return self.path.text

    @property
    def is_firmware(self) -> bool:
        """Whether the variable is the firmware's own."""
        return self.origin is VariableOrigin.FIRMWARE

    @property
    def is_bit_field(self) -> bool:
        """Whether the value is a run of bits rather than whole bytes."""
        return self.bits is not None

    @property
    def is_writable(self) -> bool:
        """Whether a client may write the variable.

        A constant may sit in memory the firmware never writes, and on a
        target it could sit in flash. Refusing to write it keeps the
        simulation honest about what the hardware would allow.
        """
        return not self.is_constant

    def value_range(self) -> tuple[float, float]:
        """Lowest and highest value this variable can hold."""
        if self.bits is not None:
            return self.encoding.bit_value_range(self.bits.width)
        return self.encoding.value_range(self.byte_width)

    def accepts(self, value: float) -> bool:
        """Whether the value fits the range this variable can hold."""
        low, high = self.value_range()
        return low <= value <= high
