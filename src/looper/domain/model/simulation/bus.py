"""Buses a firmware talks on, and the components answering on them.

A firmware reaches most of its hardware through a bus: a converter on SPI,
a port expander on I2C, a terminal on UART, the rest of the vehicle on CAN.
None of that is observable through pins or measurement channels -- what
happens is an exchange of bytes with something at an address.

So a bus is a model of its own, and what sits on it is a component. The four
kinds differ in what an address means and in how an exchange is shaped, and
that difference is kept rather than averaged away: the address carries its
kind and validates against it. What they share is what a client needs, which
is to see the buses, see what is attached, and read back what crossed.

Nothing here decides whether a component answers. That belongs to the
component, which is simulated where the firmware runs rather than here.

What crosses a bus -- a message put on one, an exchange recorded off
one -- is in `bus_traffic`. The two are separated by how often they are
made: there are four buses and a handful of components, and tens of
thousands of exchanges a second.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

#: Widest address each kind can express.
MAXIMUM_CHIP_SELECT = 0xFF
MAXIMUM_I2C_ADDRESS = 0x7F
MAXIMUM_UART_PORT = 0xFF
MAXIMUM_STANDARD_ID = 0x7FF
MAXIMUM_EXTENDED_ID = 0x1FFF_FFFF


@unique
class BusKind(Enum):
    """Which kind of bus, which decides what an address means."""

    SPI = "spi"
    I2C = "i2c"
    UART = "uart"
    CAN = "can"

    @property
    def address_name(self) -> str:
        """What this kind calls the thing an address addresses."""
        return {
            BusKind.SPI: "chip select",
            BusKind.I2C: "address",
            BusKind.UART: "port",
            BusKind.CAN: "identifier",
        }[self]

    @property
    def carries_a_response(self) -> bool:
        """Whether an exchange on this kind answers in the same breath.

        SPI clocks both ways at once and I2C reads back, so a recorded
        exchange has two halves. A UART byte and a CAN frame go one way.
        """
        return self in (BusKind.SPI, BusKind.I2C)


#: Widest address each of the addressed kinds takes. Here rather
#: than inside the check that uses it, which runs once per recorded
#: exchange and would otherwise build the same mapping every time.
WIDEST_ADDRESS = {
    BusKind.SPI: MAXIMUM_CHIP_SELECT,
    BusKind.I2C: MAXIMUM_I2C_ADDRESS,
    BusKind.UART: MAXIMUM_UART_PORT,
}


@unique
class BusDirection(Enum):
    """Which way an exchange went, from the firmware's point of view."""

    OUTBOUND = "outbound"
    INBOUND = "inbound"

    @property
    def is_from_firmware(self) -> bool:
        """Whether the firmware started the exchange rather than received it."""
        return self is BusDirection.OUTBOUND


@dataclass(frozen=True)
class BusAddress:
    """Where something sits on its bus.

    The kind is part of the identity rather than a label: chip select 2 and
    I2C address 2 are not the same place, and an identifier that fits eleven
    bits is a different identifier from the same value sent as twenty nine.

    Attributes:
        kind: Which kind of bus this address belongs to.
        value: The chip select, device address, port or identifier.
        is_extended: Only for CAN, whether the identifier is the 29 bit kind.
    """

    kind: BusKind
    value: int
    is_extended: bool = False

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"A {self.kind.address_name} must not be negative")
        if self.is_extended and self.kind is not BusKind.CAN:
            raise ValueError("Only a CAN identifier can be extended")
        if self.value > self._maximum:
            raise ValueError(
                f"{self.kind.address_name.capitalize()} {self.value} is wider "
                f"than a {self.kind.value} bus addresses"
            )

    @property
    def _maximum(self) -> int:
        """Widest value this address can hold."""
        if self.kind is BusKind.CAN:
            return MAXIMUM_EXTENDED_ID if self.is_extended else MAXIMUM_STANDARD_ID
        return WIDEST_ADDRESS[self.kind]

    @property
    def text(self) -> str:
        """The address as clients show it."""
        if self.kind is BusKind.CAN:
            return f"0x{self.value:08X}" if self.is_extended else f"0x{self.value:03X}"
        if self.kind is BusKind.I2C:
            return f"0x{self.value:02X}"
        return str(self.value)


@dataclass(frozen=True)
class SimulatedBus:
    """One bus a client can watch and address.

    Attributes:
        identifier: Opaque bus number the simulation addresses it by.
        kind: Which kind of bus it is.
        label: Readable name, for example ``CAN2`` or ``SPI1``.
        bitrate_bps: Rate the firmware configured, zero when not known.
    """

    identifier: int
    kind: BusKind
    label: str
    bitrate_bps: int = 0

    def __post_init__(self) -> None:
        if self.bitrate_bps < 0:
            raise ValueError("A bit rate must not be negative")

    @property
    def display_name(self) -> str:
        """Label if one is known, otherwise the kind and the number."""
        return self.label if self.label else f"{self.kind.value} {self.identifier}"

    @property
    def is_configured(self) -> bool:
        """Whether the firmware has set a rate on this bus."""
        return self.bitrate_bps > 0


@dataclass(frozen=True)
class ComponentDescription:
    """One simulated device, as a client sees it listed.

    The behaviour is not here. A component answers the firmware at the speed
    the firmware runs, so it is simulated in the same process; what reaches a
    client is what it is and where it sits.

    Attributes:
        bus: Bus the component is attached to.
        address: Where on that bus it answers.
        label: Readable name given at registration.
        model: What is being simulated, for example ``as8510``.
        properties: Analog channels the component publishes. A property is
            not a new kind of thing: it is a value with a name and a unit
            that a client reads, plots and sometimes drives, which is what
            a channel already is.
    """

    bus: int
    address: BusAddress
    label: str
    model: str
    properties: tuple[int, ...] = ()

    @property
    def display_name(self) -> str:
        """Label if one is known, otherwise the model and its address."""
        return self.label if self.label else f"{self.model} at {self.address.text}"

    @property
    def publishes_anything(self) -> bool:
        """Whether the component offers values beyond what crosses its bus."""
        return bool(self.properties)
