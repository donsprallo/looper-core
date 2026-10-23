"""What crosses a bus: a message put on one, an exchange recorded off one.

Separated from the bus itself because of how many there are. A
simulation models four buses and attaches a handful of components to
them; a busy second across those four is tens of thousands of
exchanges, every one of which is made into an object, given its text
and handed on. So what is done per exchange is kept together, and
kept cheap.
"""

from __future__ import annotations

from dataclasses import dataclass

from looper.domain.model.simulation.bus import BusAddress, BusDirection, BusKind

MICROSECONDS_PER_SECOND = 1_000_000

#: Longest run of bytes a client may hand to a bus in one go.
MAXIMUM_CAN_PAYLOAD = 8
MAXIMUM_SERIAL_PAYLOAD = 256


@dataclass(frozen=True)
class BusMessage:
    """What a client puts on a bus for the firmware to receive.

    Only two of the four kinds take one. On SPI and I2C the firmware is the
    master: nothing happens until it clocks, and a client that wants to
    change what it reads changes the component, not the bus.

    Attributes:
        address: Where the message is addressed, which for UART is the port.
        payload: Bytes to deliver.
    """

    address: BusAddress
    payload: bytes = b""

    def __post_init__(self) -> None:
        if self.address.kind in (BusKind.SPI, BusKind.I2C):
            raise ValueError(
                f"The firmware is the master on a {self.address.kind.value} bus, "
                f"so nothing can be sent to it"
            )
        if len(self.payload) > self._maximum_length:
            raise ValueError(
                f"A {self.address.kind.value} message carries at most "
                f"{self._maximum_length} bytes, not {len(self.payload)}"
            )

    @property
    def _maximum_length(self) -> int:
        """Longest payload this kind accepts in one message."""
        if self.address.kind is BusKind.CAN:
            return MAXIMUM_CAN_PAYLOAD
        return MAXIMUM_SERIAL_PAYLOAD

    @property
    def length(self) -> int:
        """Number of bytes the message carries."""
        return len(self.payload)

    @property
    def payload_text(self) -> str:
        """Bytes as clients show them, one hexadecimal pair each."""
        return " ".join(f"{byte:02X}" for byte in self.payload)


@dataclass(frozen=True)
class BusTraceEntry:
    """One exchange as it was recorded.

    Attributes:
        bus: Bus the exchange crossed.
        kind: Which kind of bus that is, which gives the address its meaning.
        direction: Whether the firmware started the exchange or received it.
        address: Where on the bus it was addressed.
        payload: Bytes the firmware sent.
        response: Bytes that came back, for the kinds that answer at once.
        accepted: Whether anything took the exchange. False when no component
            answered, or when a controller's filters turned a frame away.
        microseconds: Simulated time it was recorded at.
        sequence: Position in the recording, used to read incrementally.
    """

    bus: int
    kind: BusKind
    direction: BusDirection
    address: BusAddress
    payload: bytes = b""
    response: bytes = b""
    accepted: bool = True
    microseconds: int = 0
    sequence: int = 0

    @property
    def seconds(self) -> float:
        """Recording time in seconds, for lining up with the analog trace."""
        return self.microseconds / MICROSECONDS_PER_SECOND

    @property
    def length(self) -> int:
        """Number of bytes the exchange carried in the direction it went."""
        return len(self.payload) if self.payload else len(self.response)

    @property
    def was_refused(self) -> bool:
        """Whether nothing on the bus took this exchange."""
        return not self.accepted

    @property
    def payload_text(self) -> str:
        """Bytes the firmware sent, as clients show them."""
        return _hexadecimal(self.payload)

    @property
    def response_text(self) -> str:
        """Bytes that came back, as clients show them."""
        return _hexadecimal(self.response)


def _hexadecimal(payload: bytes) -> str:
    """Bytes as the pairs a person reads them in.

    Written this way rather than as a join over a formatted byte
    because a busy simulation records tens of thousands of exchanges
    a second, and every one of them is turned into text whether or
    not anybody ever scrolls back to it.
    """
    return payload.hex(" ").upper()
