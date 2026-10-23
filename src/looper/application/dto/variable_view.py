"""Data transfer objects describing the firmware variables of a build."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from looper.domain.model.firmware import VariableEncoding

BYTE_SUFFIX = "B"
FIRMWARE_ORIGIN = "firmware"
FLOATING_POINT = "float"
SIGNIFICANT_DIGITS = 6


def format_scalar(value: float, encoding: str) -> str:
    """Render a variable's value the way its own type reads.

    An integer shown in exponent notation says nothing useful: a range of
    ``0 to 4.29497e+09`` is harder to act on than ``0 to 4294967295``, and a
    count of samples is not a measurement.
    """
    if encoding == FLOATING_POINT:
        return f"{value:.{SIGNIFICANT_DIGITS}g}"
    return f"{value:.0f}"


class VariableView(BaseModel):
    """One firmware global as a client lists and picks it.

    Both addresses are carried. The link time one is what the debug
    information said and identifies the variable in the build; the runtime
    one is where it currently is, and is only meaningful for the process it
    was resolved against.

    Attributes:
        path: Full path, which is how a client searches and labels it.
        name: Last member of the path, for a column that has no room.
        root: Variable with static storage the path starts at.
        encoding: What the bytes at the address mean.
        byte_width: How many bytes the scalar occupies.
        link_time_address: Address the debug information gave.
        runtime_address: Address in the running process.
        bit_offset: First bit of the value within those bytes.
        bit_width: Bits the value occupies, or zero when it is the whole of
            the bytes at the address.
        is_writable: Whether a client may write it.
        origin: Which of the three programmes in the executable it is
            from: the firmware, the simulation, or the toolchain.
        declared_in: Source file the debug information attributes it to.
    """

    model_config = ConfigDict(frozen=True)

    path: str
    name: str
    root: str
    encoding: str
    byte_width: int
    link_time_address: int
    runtime_address: int
    is_writable: bool
    bit_offset: int = 0
    bit_width: int = 0
    origin: str = FIRMWARE_ORIGIN
    declared_in: str | None = None

    @property
    def is_firmware(self) -> bool:
        """Whether the variable is the firmware's own.

        Anything else belongs to the apparatus around it: the simulation's
        state, or the C runtime the linker brought in to make a process.
        """
        return self.origin == FIRMWARE_ORIGIN

    @property
    def is_bit_field(self) -> bool:
        """Whether the value is a run of bits rather than whole bytes."""
        return self.bit_width > 0

    @property
    def display_type(self) -> str:
        """Encoding and width as one readable string."""
        if self.is_bit_field:
            return f"{self.encoding} {self.bit_width} bit{'' if self.bit_width == 1 else 's'}"
        return f"{self.encoding} {self.byte_width} {BYTE_SUFFIX}"

    @property
    def display_address(self) -> str:
        """Link time address in hexadecimal, which is what a map file shows."""
        return f"{self.link_time_address:#x}"


class WatchView(BaseModel):
    """One firmware variable the simulation is sampling.

    Attributes:
        channel_id: Trace channel the samples are recorded on.
        path: Full path of the variable being read.
        name: Last member of the path.
        encoding: What the bytes at the address mean.
        byte_width: How many bytes the scalar occupies.
        runtime_address: Address being read in the running process.
        is_writable: Whether a client may write it.
        bit_offset: First bit of the value within those bytes.
        bit_width: Bits the value occupies, or zero when it is the whole of
            the bytes at the address.
        value: Value read at the last sample.
    """

    model_config = ConfigDict(frozen=True)

    channel_id: int
    path: str
    name: str
    encoding: str
    byte_width: int
    runtime_address: int
    is_writable: bool
    value: float
    bit_offset: int = 0
    bit_width: int = 0

    @property
    def is_bit_field(self) -> bool:
        """Whether the value is a run of bits rather than whole bytes."""
        return self.bit_width > 0

    def value_range(self) -> tuple[float, float]:
        """Lowest and highest value the watched variable can hold."""
        encoding = VariableEncoding(self.encoding)
        if self.is_bit_field:
            return encoding.bit_value_range(self.bit_width)
        return encoding.value_range(self.byte_width)

    @property
    def display_value(self) -> str:
        """Value as a client shows it, whole for an integer encoding."""
        return format_scalar(self.value, self.encoding)
