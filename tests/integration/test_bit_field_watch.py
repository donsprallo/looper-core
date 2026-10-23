"""Watching a packed flag, which is the one shape a byte cannot address.

A bit field shares its bytes with the bits around it. Reading one means
shifting and masking; writing one means putting the surrounding bits back
exactly as they were. Nothing but a running firmware can show that the
second part works.

The blinky example keeps a status word of three flags and a five bit
counter, which is the shape a firmware of that kind really uses.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from looper.domain.model.firmware import FirmwareVariable
from looper.domain.ports import SimulationRejectedError
from looper.infrastructure.ipc import ProtobufSimulationSession

LED_ON = "status.led_on"
BLINKING_FAST = "status.blinking_fast"
OVER_CURRENT = "status.over_current"
TOGGLE_COUNT = "status.toggle_count"
LIVE_FIELDS = (LED_ON, BLINKING_FAST, OVER_CURRENT, TOGGLE_COUNT)

# The example writes these once at start up and never again, so a test can
# say what they should still be after a write beside them. The live status
# word cannot: the firmware rewrites it on every toggle, and a neighbour
# that changed would say nothing about who changed it.
HAS_SHUNT = "capabilities.has_shunt"
HAS_BUTTON = "capabilities.has_button"
REVISION = "capabilities.revision"

STEP_MICROSECONDS = 5_000
FIVE_BIT_MAXIMUM = 31.0
SIX_BIT_MAXIMUM = 63.0


def test_a_packed_flag_is_found_with_the_bits_it_was_declared_with(
    variables: dict[str, FirmwareVariable],
) -> None:
    flag = variables[LED_ON]
    count = variables[TOGGLE_COUNT]

    assert flag.bits is not None
    assert count.bits is not None
    assert (flag.bits.offset, flag.bits.width) == (0, 1)
    assert (count.bits.offset, count.bits.width) == (3, 5)


def test_flags_that_share_a_byte_share_an_address(
    variables: dict[str, FirmwareVariable],
) -> None:
    """Four fields, one byte. Only the bit range tells them apart."""
    addresses = {variables[path].link_time_address for path in LIVE_FIELDS}

    assert len(addresses) == 1


def test_a_packed_counter_reads_only_its_own_bits(
    virtual_time_session: ProtobufSimulationSession,
    watch: Callable[[str], int],
    watched_value: Callable[[int], float],
) -> None:
    """The firmware counts toggles in five bits beside three flags."""
    virtual_time_session.advance_time(STEP_MICROSECONDS)

    counted = watched_value(watch(TOGGLE_COUNT))

    assert 0.0 <= counted <= FIVE_BIT_MAXIMUM


def test_the_firmware_reports_what_it_packed_at_start_up(
    watch: Callable[[str], int], watched_value: Callable[[int], float]
) -> None:
    """Three fields in one byte, each read back as the firmware set it."""
    assert watched_value(watch(HAS_SHUNT)) == 1.0
    assert watched_value(watch(HAS_BUTTON)) == 1.0
    assert watched_value(watch(REVISION)) == 3.0


def test_writing_one_field_leaves_the_bits_beside_it_alone(
    virtual_time_session: ProtobufSimulationSession,
    watch: Callable[[str], int],
    watched_value: Callable[[int], float],
) -> None:
    """The one thing a bit field write must not do is touch its neighbours.

    The revision occupies the top six bits of a byte whose low two are
    flags. A write that put the whole byte back, or shifted by the wrong
    amount, would show up here and nowhere else.
    """
    neighbours = {path: watch(path) for path in (HAS_SHUNT, HAS_BUTTON)}
    revision = watch(REVISION)
    before = {path: watched_value(channel) for path, channel in neighbours.items()}

    virtual_time_session.write_variable(revision, SIX_BIT_MAXIMUM)

    assert watched_value(revision) == SIX_BIT_MAXIMUM
    assert {path: watched_value(channel) for path, channel in neighbours.items()} == before


def test_clearing_a_neighbouring_flag_leaves_the_wider_field_alone(
    virtual_time_session: ProtobufSimulationSession,
    watch: Callable[[str], int],
    watched_value: Callable[[int], float],
) -> None:
    """The other direction: a one bit write beside a six bit field."""
    revision = watch(REVISION)
    flag = watch(HAS_SHUNT)

    virtual_time_session.write_variable(flag, 0.0)

    assert watched_value(flag) == 0.0
    assert watched_value(revision) == 3.0


def test_a_value_wider_than_the_field_is_refused(
    virtual_time_session: ProtobufSimulationSession, watch: Callable[[str], int]
) -> None:
    """Five bits hold 31. Storing 32 would come back as zero."""
    with pytest.raises(SimulationRejectedError, match="outside the range"):
        virtual_time_session.write_variable(watch(TOGGLE_COUNT), FIVE_BIT_MAXIMUM + 1.0)


def test_a_single_bit_flag_can_be_set_and_cleared(
    virtual_time_session: ProtobufSimulationSession,
    watch: Callable[[str], int],
    watched_value: Callable[[int], float],
) -> None:
    flag = watch(HAS_BUTTON)

    virtual_time_session.write_variable(flag, 0.0)
    assert watched_value(flag) == 0.0

    virtual_time_session.write_variable(flag, 1.0)
    assert watched_value(flag) == 1.0
