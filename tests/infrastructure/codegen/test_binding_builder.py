"""Turning a contract role into the call a generated adapter makes.

A role is the difference between generating a stub and generating
behaviour. What it must never do is generate something that will not
compile, so a role that names a parameter the function has not got, or
sits on a function that cannot carry a yes or no, is refused here rather
than discovered by the compiler.
"""

from __future__ import annotations

import pytest

from looper.domain.model.c_api import CFunction, CParameter, CType, CTypeKind
from looper.domain.model.contract import BusRole, BusRoleKind
from looper.infrastructure.codegen.binding_builder import RoleError, build_binding

VOID = CType(spelling="void", kind=CTypeKind.VOID)
BOOLEAN = CType(spelling="bool", kind=CTypeKind.BOOLEAN)
RESULT = CType(spelling="adapter_uart_result_t", kind=CTypeKind.ENUMERATION)
BYTE = CType(spelling="uint8_t", kind=CTypeKind.INTEGER)
LENGTH = CType(spelling="size_t", kind=CTypeKind.INTEGER)
VOID_POINTER = CType(spelling="void *", kind=CTypeKind.POINTER, pointee=VOID)
BYTES = CType(spelling="uint8_t *", kind=CTypeKind.POINTER, pointee=BYTE)
CONST_BYTES = CType(spelling="const uint8_t *", kind=CTypeKind.POINTER, pointee=BYTE, is_const=True)

TRANSFER = CFunction(
    name="adapter_spi_transfer_blocking",
    return_type=BOOLEAN,
    parameters=(
        CParameter("context", VOID_POINTER),
        CParameter("tx_data", CONST_BYTES),
        CParameter("rx_data", BYTES),
        CParameter("len", LENGTH),
    ),
)
I2C_READ = CFunction(
    name="adapter_i2c_read",
    return_type=BOOLEAN,
    parameters=(
        CParameter("context", VOID_POINTER),
        CParameter("reg", BYTE),
        CParameter("data", BYTES),
        CParameter("len", LENGTH),
    ),
)

SPI_ROLE = BusRole(
    kind=BusRoleKind.SPI_TRANSFER,
    context="context",
    transmitted="tx_data",
    received="rx_data",
    length="len",
)


def test_an_spi_transfer_becomes_a_call_to_the_bus() -> None:
    binding = build_binding(TRANSFER, SPI_ROLE)

    assert binding.bus_kind == "LOOPER_BUS_KIND_SPI"
    assert binding.instance == "context"
    assert binding.header == "looper_spi.h"
    assert binding.call == (
        "looper_spi_transfer(looper_bus, (uint8_t)looper_address, tx_data, rx_data, len)"
    )


def test_a_register_read_becomes_the_call_that_names_a_register() -> None:
    role = BusRole(
        kind=BusRoleKind.I2C_READ,
        context="context",
        register="reg",
        data="data",
        length="len",
    )

    binding = build_binding(I2C_READ, role)

    assert binding.header == "looper_i2c.h"
    assert binding.call == (
        "looper_i2c_read_register(looper_bus, (uint8_t)looper_address, reg, data, len)"
    )


def test_a_write_without_a_register_becomes_a_plain_transaction() -> None:
    function = CFunction(
        name="adapter_i2c_send",
        return_type=BOOLEAN,
        parameters=(
            CParameter("context", VOID_POINTER),
            CParameter("data", CONST_BYTES),
            CParameter("len", LENGTH),
        ),
    )
    role = BusRole(kind=BusRoleKind.I2C_WRITE, context="context", data="data", length="len")

    assert build_binding(function, role).call == (
        "looper_i2c_exchange(looper_bus, (uint8_t)looper_address, data, len, NULL, 0u)"
    )


def test_a_role_naming_a_parameter_that_is_not_there_is_refused() -> None:
    """The alternative is code the compiler rejects, which is worse."""
    role = BusRole(
        kind=BusRoleKind.SPI_TRANSFER,
        context="context",
        transmitted="outgoing",
        received="rx_data",
        length="len",
    )

    with pytest.raises(RoleError, match="no parameter called outgoing"):
        build_binding(TRANSFER, role)


def test_a_role_on_a_function_that_cannot_say_yes_or_no_is_refused() -> None:
    function = CFunction(
        name="adapter_uart_write",
        return_type=RESULT,
        parameters=(
            CParameter("context", VOID_POINTER),
            CParameter("data", CONST_BYTES),
            CParameter("len", LENGTH),
        ),
    )
    role = BusRole(kind=BusRoleKind.UART_WRITE, context="context", data="data", length="len")

    with pytest.raises(RoleError, match="returns adapter_uart_result_t"):
        build_binding(function, role)


def test_a_role_without_the_parameters_its_kind_needs_is_refused() -> None:
    with pytest.raises(ValueError, match="has to name its length"):
        BusRole(kind=BusRoleKind.SPI_TRANSFER, context="context", transmitted="tx", received="rx")
    with pytest.raises(ValueError, match="has to name its received"):
        BusRole(kind=BusRoleKind.SPI_TRANSFER, context="context", transmitted="tx", length="len")
    with pytest.raises(ValueError, match="has to name its data"):
        BusRole(kind=BusRoleKind.I2C_WRITE, context="context", length="len")


def test_a_role_knows_which_bus_it_belongs_to() -> None:
    assert BusRoleKind.SPI_TRANSFER.bus_kind == "spi"
    assert BusRoleKind.I2C_READ.bus_kind == "i2c"
    assert BusRoleKind.UART_READ.bus_kind == "uart"
