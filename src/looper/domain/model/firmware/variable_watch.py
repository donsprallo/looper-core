"""A firmware variable the simulation samples into the trace."""

from __future__ import annotations

from dataclasses import dataclass

from looper.domain.model.firmware.firmware_variable import FirmwareVariable

MAXIMUM_CHANNEL_VALUE = 0xFFFF_FFFF


@dataclass(frozen=True)
class VariableWatch:
    """One variable the simulation reads on every firmware loop iteration.

    Sampling happens inside the simulation for the same reason signals are
    evaluated there: a client can only poll as fast as the network allows,
    and would see a staircase of whatever happened to fall on a poll. A watch
    records at the rate the firmware runs at.

    The channel number is what the trace is keyed by. It is allocated by the
    simulation, not chosen by the client, and it is what lets a watched
    variable be plotted beside the analog channels the firmware registered.

    Attributes:
        channel: Trace channel the samples are recorded on.
        variable: Variable being read.
        runtime_address: Address in the running process, already relocated.
        value: Value read at the last sample.
    """

    channel: int
    variable: FirmwareVariable
    runtime_address: int
    value: float = 0.0

    def __post_init__(self) -> None:
        if not 0 <= self.channel <= MAXIMUM_CHANNEL_VALUE:
            raise ValueError(f"Channel {self.channel} is outside the 32 bit range")
        if self.runtime_address <= 0:
            raise ValueError(f"Watch on '{self.variable.path}' has no usable address")

    @property
    def display_name(self) -> str:
        """Full variable path, which is what a client labels the plot with."""
        return self.variable.display_name

    @property
    def is_drivable_by_client(self) -> bool:
        """Whether a client may write the variable this watch reads."""
        return self.variable.is_writable

    def accepts(self, value: float) -> bool:
        """Whether the value fits the range the watched variable can hold."""
        return self.variable.accepts(value)
