"""Default values of generated adapter functions."""

from __future__ import annotations

import pytest

from looper.domain.model.c_api import CType, CTypeKind
from looper.infrastructure.codegen.c_defaults import default_return_expression

VOID = CType(spelling="void", kind=CTypeKind.VOID)


@pytest.mark.parametrize(
    ("kind", "spelling", "expected"),
    [
        (CTypeKind.BOOLEAN, "bool", "false"),
        (CTypeKind.INTEGER, "uint32_t", "0"),
        (CTypeKind.FLOATING, "float", "0.0"),
        (CTypeKind.ENUMERATION, "adapter_can_result_t", "(adapter_can_result_t)0"),
        (CTypeKind.RECORD, "demo_value_t", "(demo_value_t){0}"),
    ],
)
def test_every_default_is_the_zero_value(kind: CTypeKind, spelling: str, expected: str) -> None:
    assert default_return_expression(CType(spelling=spelling, kind=kind)) == expected


def test_a_pointer_defaults_to_null() -> None:
    pointer = CType(spelling="uint8_t *", kind=CTypeKind.POINTER, pointee=VOID)

    assert default_return_expression(pointer) == "NULL"


def test_a_void_function_returns_nothing() -> None:
    assert default_return_expression(VOID) is None
