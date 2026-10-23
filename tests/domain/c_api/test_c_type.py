"""Invariants of the parsed C type model."""

from __future__ import annotations

import pytest

from looper.domain.model.c_api import CType, CTypeKind

VOID = CType(spelling="void", kind=CTypeKind.VOID)
CONST_BYTE = CType(spelling="const uint8_t", kind=CTypeKind.INTEGER, is_const=True)


def test_pointer_requires_a_pointee() -> None:
    with pytest.raises(ValueError, match="requires a pointee"):
        CType(spelling="uint8_t *", kind=CTypeKind.POINTER)


def test_blank_spelling_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        CType(spelling="  ", kind=CTypeKind.INTEGER)


def test_pointer_to_void_is_an_opaque_handle() -> None:
    handle = CType(spelling="void *", kind=CTypeKind.POINTER, pointee=VOID)

    assert handle.is_opaque_handle
    assert handle.carries_memory


def test_pointer_to_const_payload_is_read_only() -> None:
    buffer = CType(spelling="const uint8_t *", kind=CTypeKind.POINTER, pointee=CONST_BYTE)

    assert buffer.points_to_const
    assert not buffer.is_opaque_handle
