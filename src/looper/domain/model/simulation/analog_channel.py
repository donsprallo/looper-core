"""Analog channels, the signals that drive them, and what they recorded."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

MICROSECONDS_PER_SECOND = 1_000_000


@unique
class Waveform(Enum):
    """Shape of a generated signal."""

    CONSTANT = "constant"
    SINE = "sine"
    SQUARE = "square"
    TRIANGLE = "triangle"
    SAWTOOTH = "sawtooth"

    @property
    def is_alternating(self) -> bool:
        """Whether the waveform swings rather than holding a level."""
        return self is not Waveform.CONSTANT

    @property
    def display_name(self) -> str:
        """Readable name for a client to show."""
        return "DC" if self is Waveform.CONSTANT else self.value.capitalize()


@unique
class ChannelDirection(Enum):
    """Whether the firmware reads an analog channel or writes it."""

    INPUT = "input"
    OUTPUT = "output"


@dataclass(frozen=True)
class SignalDefinition:
    """What a generator produces on one channel.

    ``CONSTANT`` uses the offset alone, which is how a DC level is expressed.
    Every other waveform swings by the amplitude around the offset.

    Attributes:
        waveform: Shape of the signal.
        amplitude: Peak deviation from the offset.
        offset: Level the signal is centred on.
        frequency_hz: Repetitions per second.
        phase_degrees: Shift within one period.
    """

    waveform: Waveform = Waveform.CONSTANT
    amplitude: float = 0.0
    offset: float = 0.0
    frequency_hz: float = 0.0
    phase_degrees: float = 0.0

    def __post_init__(self) -> None:
        if self.frequency_hz < 0.0:
            raise ValueError("A signal frequency must not be negative")
        if self.amplitude < 0.0:
            raise ValueError("A signal amplitude must not be negative")

    @property
    def is_static(self) -> bool:
        """Whether the signal holds one level rather than moving."""
        return not self.waveform.is_alternating or self.frequency_hz == 0.0

    @property
    def minimum(self) -> float:
        """Lowest value the signal reaches."""
        return self.offset if self.is_static else self.offset - self.amplitude

    @property
    def maximum(self) -> float:
        """Highest value the signal reaches."""
        return self.offset if self.is_static else self.offset + self.amplitude

    @property
    def period_seconds(self) -> float | None:
        """Duration of one period, or ``None`` for a static signal."""
        if self.is_static:
            return None
        return 1.0 / self.frequency_hz


@dataclass(frozen=True)
class AnalogChannel:
    """One analog channel as a client observes it.

    Attributes:
        identifier: Opaque channel number used by the firmware.
        label: Readable channel name.
        unit: Unit the value is measured in.
        direction: Whether the firmware reads or writes the channel.
        value: Value last read or written.
        signal: Signal driving the channel, for inputs.
        has_value: Whether anything has ever written to the channel. A
            channel the firmware registers but never publishes reads
            zero, and so does one that is publishing zero; the first is
            usually a feature the firmware has switched off.
    """

    identifier: int
    label: str
    unit: str
    direction: ChannelDirection
    value: float
    signal: SignalDefinition = SignalDefinition()
    has_value: bool = True

    @property
    def display_name(self) -> str:
        """Label if one is known, otherwise the channel number."""
        return self.label if self.label else f"channel {self.identifier}"

    @property
    def is_drivable_by_client(self) -> bool:
        """Whether a client may install a signal, which only applies to inputs."""
        return self.direction is ChannelDirection.INPUT

    @property
    def is_silent(self) -> bool:
        """Whether the firmware has never published anything here.

        Worth saying out loud. A registered channel that stays empty is
        almost always a calculation the firmware has switched off in
        its configuration, and a zero that means "off" looks exactly
        like a zero that means zero.
        """
        return not self.has_value


@dataclass(frozen=True)
class AnalogSample:
    """One recorded value of one channel.

    Attributes:
        channel: Channel the value belongs to.
        microseconds: Simulated time the value was recorded at.
        value: Value that was read or written.
        sequence: Position in the recording, used to read incrementally.
    """

    channel: int
    microseconds: int
    value: float
    sequence: int

    @property
    def seconds(self) -> float:
        """Recording time in seconds, for plotting."""
        return self.microseconds / MICROSECONDS_PER_SECOND
