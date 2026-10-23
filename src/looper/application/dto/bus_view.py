"""Data transfer objects describing the buses of a simulation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

UNKNOWN_BITRATE = "not configured"
KILOBITS_PER_SECOND = 1000
KINDS_A_CLIENT_CAN_DRIVE = ("can", "uart")


class BusView(BaseModel):
    """One bus as a client displays and addresses it.

    Attributes:
        bus_id: Opaque bus number the simulation addresses it by.
        kind: Which kind of bus it is.
        name: Readable bus name.
        bitrate_bps: Rate the firmware configured, zero when not known.
    """

    model_config = ConfigDict(frozen=True)

    bus_id: int
    kind: str
    name: str
    bitrate_bps: int

    @property
    def display_bitrate(self) -> str:
        """Rate as a readable string, or a note that there is none."""
        if self.bitrate_bps == 0:
            return UNKNOWN_BITRATE
        return f"{self.bitrate_bps // KILOBITS_PER_SECOND} kbit/s"

    @property
    def accepts_messages(self) -> bool:
        """Whether a client may put something on this bus.

        On SPI and I2C the firmware is the master: nothing happens until it
        clocks, so a client changes the component rather than the bus.
        """
        return self.kind in KINDS_A_CLIENT_CAN_DRIVE


class ComponentView(BaseModel):
    """One simulated device as a client sees it listed.

    Attributes:
        bus_id: Bus the component is attached to.
        address: Where on that bus it answers, as it is shown.
        name: Readable component name.
        model: What is being simulated.
        properties: Channels the component publishes, which a client plots
            and drives like any other.
    """

    model_config = ConfigDict(frozen=True)

    bus_id: int
    address: str
    name: str
    model: str
    properties: tuple[int, ...] = ()


class ExchangeView(BaseModel):
    """One recorded exchange, ready to be listed.

    Attributes:
        bus_id: Bus the exchange crossed.
        kind: Which kind of bus that is.
        seconds: Simulated time it was recorded at.
        direction: Whether the firmware started it or received it.
        address: Where it was addressed, as it is shown.
        length: Number of bytes it carried.
        payload: Bytes the firmware sent, as hexadecimal pairs.
        response: Bytes that came back, as hexadecimal pairs.
        accepted: Whether anything took the exchange.
        sequence: Position in the recording.
    """

    model_config = ConfigDict(frozen=True)

    bus_id: int
    kind: str
    seconds: float
    direction: str
    address: str
    length: int
    payload: str
    response: str
    accepted: bool
    sequence: int

    @property
    def was_refused(self) -> bool:
        """Whether nothing on the bus took this exchange."""
        return not self.accepted


class BusTraceView(BaseModel):
    """A batch of recorded exchanges and where to continue reading.

    Attributes:
        exchanges: Recorded exchanges, oldest first.
        next_sequence: Sequence number to ask for next.
    """

    model_config = ConfigDict(frozen=True)

    exchanges: tuple[ExchangeView, ...]
    next_sequence: int
