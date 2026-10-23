"""Turning a contract role into the call a generated adapter makes.

A role says that a function *is* an SPI transfer, and which of its
parameters is the buffer going out. That is everything needed to write the
call, and writing it here is what saves a project from writing it by hand
in every adapter it simulates.

Two things are checked before anything is written, because the alternative
is generated code that does not compile. Every parameter a role names has
to exist on the function, and the function has to report success the way
the bus models do.
"""

from __future__ import annotations

from looper.domain.model.c_api import CFunction
from looper.domain.model.contract import BusRole, BusRoleKind
from looper.infrastructure.codegen.view_model import BindingView

#: Variables the generated code resolves the place into.
BUS = "looper_bus"
ADDRESS = "looper_address"

#: Return types a role may sit on. A bus model answers with a plain yes or
#: no, and anything else would need a translation the contract cannot give.
BOOLEAN_TYPES = frozenset({"bool", "_Bool"})

BUS_KIND_ENUMERATORS = {
    "spi": "LOOPER_BUS_KIND_SPI",
    "i2c": "LOOPER_BUS_KIND_I2C",
    "uart": "LOOPER_BUS_KIND_UART",
}
BUS_HEADERS = {
    "spi": "looper_spi.h",
    "i2c": "looper_i2c.h",
    "uart": "looper_uart.h",
}

DESCRIPTIONS = {
    BusRoleKind.SPI_TRANSFER: "a transfer on an SPI bus",
    BusRoleKind.I2C_READ: "a read from a device on an I2C bus",
    BusRoleKind.I2C_WRITE: "a write to a device on an I2C bus",
    BusRoleKind.UART_WRITE: "bytes written to a UART port",
    BusRoleKind.UART_READ: "bytes read from a UART port",
}


class RoleError(ValueError):
    """A role the generator cannot turn into code that would compile."""


def build_binding(function: CFunction, role: BusRole) -> BindingView:
    """Describe the call a function with this role should make.

    Raises:
        RoleError: If the role names a parameter the function does not
            have, or sits on a function that cannot report a yes or no.
    """
    _ensure_parameters_exist(function, role)
    _ensure_answers_yes_or_no(function)
    return BindingView(
        description=DESCRIPTIONS[role.kind],
        instance=role.context,
        bus_kind=BUS_KIND_ENUMERATORS[role.kind.bus_kind],
        call=_call_of(role),
        header=BUS_HEADERS[role.kind.bus_kind],
    )


def _ensure_parameters_exist(function: CFunction, role: BusRole) -> None:
    """Insist that every parameter the role names is really there."""
    declared = {parameter.name for parameter in function.parameters}
    missing = sorted(set(role.named_parameters) - declared)
    if missing:
        raise RoleError(
            f"'{function.name}' has no parameter called {', '.join(missing)}, "
            f"which its '{role.kind.value}' role names"
        )


def _ensure_answers_yes_or_no(function: CFunction) -> None:
    """Insist that the function can carry the answer a bus model gives."""
    if function.return_type.spelling not in BOOLEAN_TYPES:
        raise RoleError(
            f"'{function.name}' returns {function.return_type.spelling}, and a role "
            f"needs a function returning bool: a bus answers yes or no, and what "
            f"anything else means is the adapter's own business"
        )


def _call_of(role: BusRole) -> str:
    """The complete call, in terms of the resolved bus and address."""
    address = f"(uint8_t){ADDRESS}"
    if role.kind is BusRoleKind.SPI_TRANSFER:
        return (
            f"looper_spi_transfer({BUS}, {address}, "
            f"{role.transmitted}, {role.received}, {role.length})"
        )
    if role.kind is BusRoleKind.UART_WRITE:
        return f"looper_uart_write({BUS}, {address}, {role.data}, {role.length})"
    if role.kind is BusRoleKind.UART_READ:
        return f"looper_uart_read({BUS}, {address}, {role.data}, {role.length}) > 0u"
    return _i2c_call(role, address)


def _i2c_call(role: BusRole, address: str) -> str:
    """The I2C call, with or without the register a HAL usually asks for."""
    direction = "read" if role.kind is BusRoleKind.I2C_READ else "write"
    if role.register is None:
        transmitted = role.data if direction == "write" else "NULL"
        received = role.data if direction == "read" else "NULL"
        sent_length = role.length if direction == "write" else "0u"
        read_length = role.length if direction == "read" else "0u"
        return (
            f"looper_i2c_exchange({BUS}, {address}, {transmitted}, {sent_length}, "
            f"{received}, {read_length})"
        )
    return (
        f"looper_i2c_{direction}_register({BUS}, {address}, "
        f"{role.register}, {role.data}, {role.length})"
    )
