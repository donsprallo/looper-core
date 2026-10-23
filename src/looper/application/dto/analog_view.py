"""Data transfer objects describing the analog side of a simulation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SignalView(BaseModel):
    """A signal definition as a client edits it.

    Attributes:
        waveform: Shape of the signal.
        amplitude: Peak deviation from the offset.
        offset: Level the signal is centred on.
        frequency_hz: Repetitions per second.
        phase_degrees: Shift within one period.
    """

    model_config = ConfigDict(frozen=True)

    waveform: str
    amplitude: float
    offset: float
    frequency_hz: float
    phase_degrees: float


class ChannelView(BaseModel):
    """One analog channel as a client displays and drives it.

    Attributes:
        channel_id: Opaque channel number used by the firmware.
        name: Readable channel name.
        unit: Unit the value is measured in.
        direction: Whether the firmware reads or writes the channel.
        value: Value last read or written.
        is_drivable: Whether a client may install a signal.
        signal: Signal driving the channel.
        is_silent: Whether the firmware has never published anything
            here, which reads the same as a value of zero and means
            something quite different.
    """

    model_config = ConfigDict(frozen=True)

    channel_id: int
    name: str
    unit: str
    direction: str
    value: float
    is_drivable: bool
    signal: SignalView
    is_silent: bool = False

    @property
    def display_value(self) -> str:
        """Value and unit as one readable string.

        A channel nothing has ever written says so rather than showing
        a zero it does not have. The firmware registered it and then
        published nothing, which usually means the calculation behind
        it is switched off in the firmware's configuration.
        """
        if self.is_silent:
            return "no data"
        return f"{self.value:.4g} {self.unit}".strip()


class SampleView(BaseModel):
    """One recorded value, ready to be plotted.

    Attributes:
        channel_id: Channel the value belongs to.
        seconds: Simulated time the value was recorded at.
        value: Value that was read or written.
        sequence: Position in the recording.
    """

    model_config = ConfigDict(frozen=True)

    channel_id: int
    seconds: float
    value: float
    sequence: int


class TraceView(BaseModel):
    """A batch of recorded samples and where to continue reading.

    Attributes:
        samples: Recorded values, oldest first.
        next_sequence: Sequence number to ask for next.
    """

    model_config = ConfigDict(frozen=True)

    samples: tuple[SampleView, ...]
    next_sequence: int
