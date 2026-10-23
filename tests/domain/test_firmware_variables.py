"""Invariants of the firmware variable model."""

from __future__ import annotations

import pytest

from looper.domain.model.firmware import (
    FirmwareVariable,
    LoadedImage,
    VariableEncoding,
    VariablePath,
    VariableWatch,
)

GAIN_PATH = "g_app_config.active.measurement.channel[0].calibration.gain"
LINK_TIME_BASE = 0x1_4000_0000
RUNTIME_BASE = 0x7FF7_9600_0000


def a_variable(
    path: str = GAIN_PATH,
    address: int = 0x1_4007_11A8,
    encoding: VariableEncoding = VariableEncoding.FLOATING_POINT,
    byte_width: int = 8,
    is_constant: bool = False,
) -> FirmwareVariable:
    """Build a variable, so that a test names only what it is about."""
    return FirmwareVariable(
        path=VariablePath(path),
        link_time_address=address,
        encoding=encoding,
        byte_width=byte_width,
        is_constant=is_constant,
    )


def test_a_path_knows_the_variable_it_starts_at() -> None:
    path = VariablePath(GAIN_PATH)

    assert path.root == "g_app_config"
    assert path.leaf == "gain"
    assert not path.is_root


def test_a_path_without_members_is_its_own_root_and_leaf() -> None:
    path = VariablePath("g_application_runtime")

    assert path.root == path.leaf == "g_application_runtime"
    assert path.is_root


def test_a_subscript_belongs_to_the_member_it_indexes() -> None:
    path = VariablePath("g_app_config.channel[0]")

    assert path.root == "g_app_config"
    assert path.leaf == "channel[0]"


def test_an_empty_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        VariablePath("   ")


def test_an_unsigned_byte_holds_zero_to_two_hundred_fifty_five() -> None:
    encoding = VariableEncoding.UNSIGNED_INTEGER

    assert encoding.value_range(1) == (0.0, 255.0)
    assert encoding.accepts(255.0, 1)
    assert not encoding.accepts(256.0, 1)
    assert not encoding.accepts(-1.0, 1)


def test_a_signed_byte_is_asymmetric_around_zero() -> None:
    assert VariableEncoding.SIGNED_INTEGER.value_range(1) == (-128.0, 127.0)


def test_a_boolean_holds_only_zero_and_one() -> None:
    encoding = VariableEncoding.BOOLEAN

    assert encoding.supported_byte_widths == (1,)
    assert encoding.value_range(1) == (0.0, 1.0)
    assert not encoding.accepts(2.0, 1)


def test_only_floating_point_values_are_fractional() -> None:
    assert not VariableEncoding.FLOATING_POINT.is_integral
    assert VariableEncoding.SIGNED_INTEGER.is_integral
    assert VariableEncoding.BOOLEAN.is_integral


def test_an_encoding_rejects_a_width_it_has_no_form_for() -> None:
    with pytest.raises(ValueError, match="no 3 byte form"):
        VariableEncoding.FLOATING_POINT.value_range(3)


def test_a_variable_of_an_impossible_width_is_rejected() -> None:
    with pytest.raises(ValueError, match="not a float width"):
        a_variable(encoding=VariableEncoding.FLOATING_POINT, byte_width=2)


def test_a_variable_without_an_address_is_rejected() -> None:
    with pytest.raises(ValueError, match="no usable address"):
        a_variable(address=0)


def test_a_constant_variable_may_not_be_written() -> None:
    assert not a_variable(is_constant=True).is_writable
    assert a_variable().is_writable


def test_a_variable_checks_a_value_against_its_own_width() -> None:
    counter = a_variable(encoding=VariableEncoding.UNSIGNED_INTEGER, byte_width=2)

    assert counter.accepts(65535.0)
    assert not counter.accepts(65536.0)


def test_the_declaring_file_does_not_change_which_variable_it_is() -> None:
    here = FirmwareVariable(
        path=VariablePath("g_counter"),
        link_time_address=0x1_4007_0000,
        encoding=VariableEncoding.UNSIGNED_INTEGER,
        byte_width=4,
        declared_in="app.c",
    )
    there = FirmwareVariable(
        path=VariablePath("g_counter"),
        link_time_address=0x1_4007_0000,
        encoding=VariableEncoding.UNSIGNED_INTEGER,
        byte_width=4,
        declared_in="bsp.c",
    )

    assert here == there


def test_a_relocated_image_moves_every_address_by_the_same_distance() -> None:
    image = LoadedImage(link_time_base=LINK_TIME_BASE, runtime_base=RUNTIME_BASE)

    assert image.is_relocated
    assert image.slide == RUNTIME_BASE - LINK_TIME_BASE
    assert image.runtime_address_of(a_variable()) == 0x1_4007_11A8 + image.slide


def test_an_image_loaded_where_it_was_linked_moves_nothing() -> None:
    image = LoadedImage(link_time_base=LINK_TIME_BASE, runtime_base=LINK_TIME_BASE)

    assert not image.is_relocated
    assert image.runtime_address_of(a_variable()) == 0x1_4007_11A8


def test_debug_information_from_another_build_is_rejected() -> None:
    image = LoadedImage(link_time_base=0x7FFF_FFFF_FFFF, runtime_base=1)

    with pytest.raises(ValueError, match="does not belong to this process"):
        image.runtime_address_of(a_variable())


def test_a_watch_carries_the_drivability_of_its_variable() -> None:
    watched = VariableWatch(channel=0x8000_0001, variable=a_variable(), runtime_address=0x1000)
    constant = VariableWatch(
        channel=0x8000_0002, variable=a_variable(is_constant=True), runtime_address=0x1000
    )

    assert watched.is_drivable_by_client
    assert not constant.is_drivable_by_client
    assert watched.display_name == GAIN_PATH


def test_a_watch_without_a_usable_address_is_rejected() -> None:
    with pytest.raises(ValueError, match="no usable address"):
        VariableWatch(channel=1, variable=a_variable(), runtime_address=0)
