"""Bit fields against a real compiler's idea of where they sit.

A packed field is the one case where the reader cannot be checked by
arithmetic alone: how many bits each field gets, and in what order, is the
compiler's decision. The fixture declares a layout and the reader has to
describe the one the compiler actually produced.
"""

from __future__ import annotations

from looper.domain.model.firmware import FirmwareVariable, VariableEncoding


def test_a_packed_field_carries_the_bits_it_was_declared_with(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    enabled = fixture_variables["g_packed.enabled"]
    mode = fixture_variables["g_packed.mode"]

    assert enabled.is_bit_field
    assert enabled.bits is not None
    assert mode.bits is not None
    assert (enabled.bits.offset, enabled.bits.width) == (0, 1)
    assert (mode.bits.offset, mode.bits.width) == (1, 3)


def test_a_signed_packed_field_keeps_its_sign(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    """Four signed bits hold -8 to 7, which is not a byte's range."""
    trim = fixture_variables["g_packed.trim"]

    assert trim.encoding is VariableEncoding.SIGNED_INTEGER
    assert trim.value_range() == (-8.0, 7.0)
    assert trim.accepts(7.0)
    assert not trim.accepts(8.0)


def test_a_packed_field_is_addressed_at_the_byte_its_bits_fall_in(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    """A field past the first byte moves its address, not just its offset."""
    enabled = fixture_variables["g_packed.enabled"]
    serial = fixture_variables["g_packed.serial"]

    assert serial.bits is not None
    assert serial.bits.width == 12
    assert serial.link_time_address > enabled.link_time_address
    assert serial.byte_width == serial.bits.byte_width


def test_packed_fields_of_one_byte_share_an_address(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    shared = {
        fixture_variables[f"g_packed.{name}"].link_time_address for name in ("enabled", "mode")
    }

    assert len(shared) == 1
