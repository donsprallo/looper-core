"""What an adapter function does, when what it does is use a bus.

A contract already says what a parameter means: which one is a buffer, who
owns it, when it is written. That is enough to generate a stub but not
enough to generate behaviour, because a stub does not know that
``adapter_spi_transfer_blocking`` *is* an SPI transfer rather than one more
function returning false.

A role says exactly that, and names which parameter plays which part. With
it the generator writes the binding a project otherwise writes by hand: the
translation from a HAL's own shape -- a context pointer standing for a
device, a register number where an address belongs -- onto a bus and an
address.

Three of the four kinds are here. CAN is not, and deliberately: a frame is
a structure whose fields the contract would have to describe field by
field, and what a CAN controller mostly does is apply acceptance filters,
which is a decision rather than a translation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

from looper.domain.model.c_api.validation import ensure_non_empty


@unique
class BusRoleKind(Enum):
    """Which bus operation an adapter function carries out."""

    SPI_TRANSFER = "spi.transfer"
    I2C_READ = "i2c.read"
    I2C_WRITE = "i2c.write"
    UART_WRITE = "uart.write"
    UART_READ = "uart.read"

    @property
    def bus_kind(self) -> str:
        """The kind of bus this role belongs to."""
        return self.value.split(".")[0]

    @property
    def needs_data(self) -> bool:
        """Whether the role carries a buffer of bytes."""
        return self is not BusRoleKind.SPI_TRANSFER

    @property
    def reads_back(self) -> bool:
        """Whether the buffer is filled rather than sent."""
        return self in (BusRoleKind.I2C_READ, BusRoleKind.UART_READ)


@dataclass(frozen=True)
class BusRole:
    """What one adapter function does on a bus, and with which parameters.

    Every parameter named here must exist on the function; the generator
    checks that before it writes anything, because a role naming a
    parameter that is not there would produce code that does not compile.

    Attributes:
        kind: Which bus operation this is.
        context: Parameter holding the instance that says which device.
        data: Parameter holding the bytes, for the kinds that carry them.
        length: Parameter holding how many bytes.
        transmitted: Parameter holding the bytes sent, for SPI.
        received: Parameter holding the bytes clocked back, for SPI.
        register: Parameter holding a register number written before the
            data, which a HAL offers instead of letting the caller build
            the bytes itself.
    """

    kind: BusRoleKind
    context: str
    data: str | None = None
    length: str | None = None
    transmitted: str | None = None
    received: str | None = None
    register: str | None = None

    def __post_init__(self) -> None:
        ensure_non_empty(self.context, "A role context parameter")
        if self.length is None:
            raise ValueError(f"A '{self.kind.value}' role has to name its length parameter")
        if self.kind is BusRoleKind.SPI_TRANSFER:
            self._ensure_named("transmitted", self.transmitted)
            self._ensure_named("received", self.received)
            return
        self._ensure_named("data", self.data)

    def _ensure_named(self, part: str, value: str | None) -> None:
        """Insist on a parameter name this kind of role cannot do without."""
        if not value:
            raise ValueError(f"A '{self.kind.value}' role has to name its {part} parameter")

    @property
    def named_parameters(self) -> tuple[str, ...]:
        """Every parameter this role refers to, in no particular order."""
        named = (
            self.context,
            self.data,
            self.length,
            self.transmitted,
            self.received,
            self.register,
        )
        return tuple(name for name in named if name)
