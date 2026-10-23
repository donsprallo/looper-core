"""The variable reader against a real compiler's debug information.

The reader claims that a path like ``config.channel[1].gain`` names an
address. Only a compiler can say whether that address is right, because only
the compiler decides where padding goes. So the fixture is compiled and the
reader checked against what the C program itself reports about its layout.
The fixture and its build live in conftest.py, which the bit field reader
tests share.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.domain.model.firmware import FirmwareVariable, VariableEncoding
from looper.infrastructure.debug import DebugInformationError, DwarfDebugReader


def _offsets(fixture_build: tuple[Path, tuple[int, int, int]]) -> tuple[int, int, int]:
    """Member offsets the compiled program reported about itself."""
    return fixture_build[1]


def test_a_nested_member_sits_where_the_compiler_put_it(
    fixture_variables: dict[str, FirmwareVariable],
    fixture_build: tuple[Path, tuple[int, int, int]],
) -> None:
    base = fixture_variables["g_config.channel[0].enabled"].link_time_address
    calibration_offset, gain_offset, _ = _offsets(fixture_build)

    assert (
        fixture_variables["g_config.channel[1].calibration[0].offset_counts"].link_time_address
        == base + calibration_offset
    )
    assert fixture_variables["g_config.channel[2].gain"].link_time_address == base + gain_offset


def test_every_scalar_of_a_structure_is_reached(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    expected = {
        f"g_config.channel[{index}].{member}"
        for index in range(3)
        for member in (
            "enabled",
            "sample_rate_hz",
            "calibration[0].numerator",
            "calibration[0].offset_counts",
            "calibration[1].numerator",
            "calibration[1].offset_counts",
            "gain",
        )
    }

    assert expected <= set(fixture_variables)


def test_each_scalar_carries_the_encoding_it_was_declared_with(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    assert fixture_variables["g_config.channel[0].enabled"].encoding is VariableEncoding.BOOLEAN
    assert fixture_variables["g_config.channel[0].gain"].encoding is VariableEncoding.FLOATING_POINT
    assert fixture_variables["g_config.channel[0].gain"].byte_width == 8
    assert (
        fixture_variables["g_config.channel[0].calibration[0].offset_counts"].encoding
        is VariableEncoding.SIGNED_INTEGER
    )
    assert fixture_variables["g_unused_elsewhere"].encoding is VariableEncoding.FLOATING_POINT
    assert fixture_variables["g_unused_elsewhere"].byte_width == 4


def test_a_const_variable_is_reported_as_one(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    assert fixture_variables["g_revision"].is_constant
    assert not fixture_variables["g_revision"].is_writable
    assert not fixture_variables["g_temperature"].is_constant


def test_a_pointer_is_not_offered(fixture_variables: dict[str, FirmwareVariable]) -> None:
    """Its value is an address, which says where something is, not what it is."""
    assert "g_config.name" not in fixture_variables


def test_a_structure_of_nothing_but_pointers_is_not_offered(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    """A vtable has nothing to watch, so it is not a branch to open either."""
    assert not [path for path in fixture_variables if path.startswith("g_vtable")]


def test_the_scalars_beside_a_pointer_are_still_offered(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    """Leaving the pointer out must not take its neighbours with it."""
    assert "g_config.channel[0].gain" in fixture_variables
    assert "g_mixed.counter" in fixture_variables


def test_a_static_inside_a_function_is_not_a_global(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    assert not [path for path in fixture_variables if path.endswith("g_calls")]


def test_a_file_scope_static_is_a_global(fixture_variables: dict[str, FirmwareVariable]) -> None:
    assert "g_sequence" in fixture_variables
    assert fixture_variables["g_sequence"].encoding is VariableEncoding.UNSIGNED_INTEGER
    assert fixture_variables["g_sequence"].byte_width == 8


def test_a_width_no_encoding_has_a_form_for_is_left_out(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    assert "g_wide_one" not in fixture_variables


def test_the_declaring_source_file_is_reported(
    fixture_variables: dict[str, FirmwareVariable],
) -> None:
    assert fixture_variables["g_revision"].declared_in is not None
    assert fixture_variables["g_revision"].declared_in.endswith("fixture.c")


def test_an_executable_that_does_not_exist_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No simulation executable"):
        DwarfDebugReader().read_variables(tmp_path / "absent")


def test_a_file_that_is_not_an_executable_is_reported(tmp_path: Path) -> None:
    text = tmp_path / "notes.txt"
    text.write_text("not an executable", encoding="utf-8")

    with pytest.raises(DebugInformationError, match="neither an ELF nor a Windows executable"):
        DwarfDebugReader().read_variables(text)
