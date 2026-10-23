"""Invariants of the parsed function model."""

from __future__ import annotations

import pytest

from looper.domain.model.c_api import CFunction, CParameter, CType, CTypeKind

BOOLEAN = CType(spelling="bool", kind=CTypeKind.BOOLEAN)
VOID = CType(spelling="void", kind=CTypeKind.VOID)
BYTE = CType(spelling="uint8_t", kind=CTypeKind.INTEGER)
BYTE_POINTER = CType(spelling="uint8_t *", kind=CTypeKind.POINTER, pointee=BYTE)


def test_duplicate_parameter_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate names: data"):
        CFunction(
            name="adapter_spi_transfer",
            return_type=BOOLEAN,
            parameters=(CParameter("data", BYTE_POINTER), CParameter("data", BYTE_POINTER)),
        )


def test_a_void_function_returns_no_value() -> None:
    function = CFunction(name="panic", return_type=VOID)

    assert not function.returns_value
    assert function.parameter_names == ()


def test_parameter_lookup_names_the_function_it_failed_on() -> None:
    function = CFunction(name="adapter_flash_read", return_type=BOOLEAN)

    with pytest.raises(KeyError, match="adapter_flash_read"):
        function.parameter("address")
