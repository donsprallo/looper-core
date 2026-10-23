"""Watching a firmware variable, from the debug information to the trace.

Three things have to agree for a watch to work, and only a running
simulation can show that they do: the address the debug information gives,
the distance the loader moved the image by, and what the firmware actually
has in memory. A unit test can check each in isolation and still miss that
they describe different places.

The firmware is the blinky example, which keeps a filtered measurement in a
file scope ``double``. That variable moves while the firmware runs and
changes what the firmware does when it is written, so it exercises both
directions.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from looper.domain.model.firmware import (
    FirmwareVariable,
    LoadedImage,
    VariableEncoding,
    VariableOrigin,
)
from looper.domain.ports import SimulationRejectedError
from looper.infrastructure.ipc import ProtobufSimulationSession

FILTERED_CURRENT = "filtered_current"
LAST_TOGGLE = "last_toggle_ms"
WATCH_CHANNEL_BASE = 0x8000_0000

# Enough simulated time for the firmware to take a sample and the loop to
# poll its watches; the example samples once per millisecond.
STEP_MICROSECONDS = 5_000

# Far enough above anything the example measures that the value is still
# recognisable after the filter has pulled on it for a while.
WRITTEN_VALUE = 1000.0


def test_the_simulation_reports_where_it_was_loaded(image: LoadedImage, executable: Path) -> None:
    assert executable.is_file()
    assert image.runtime_base > 0


def test_a_firmware_global_is_found_with_the_type_it_was_declared_with(
    variables: dict[str, FirmwareVariable],
) -> None:
    assert variables[FILTERED_CURRENT].encoding is VariableEncoding.FLOATING_POINT
    assert variables[FILTERED_CURRENT].byte_width == 8
    assert variables[LAST_TOGGLE].encoding is VariableEncoding.UNSIGNED_INTEGER
    assert variables[LAST_TOGGLE].byte_width == 4


def test_a_watched_variable_reports_what_the_firmware_has_in_memory(
    virtual_time_session: ProtobufSimulationSession,
    watch: Callable[[str], int],
    watched_value: Callable[[int], float],
) -> None:
    """The firmware sets this one from the clock, so it is not zero."""
    virtual_time_session.advance_time(STEP_MICROSECONDS)

    assert watched_value(watch(LAST_TOGGLE)) > 0.0


def test_a_watch_is_given_a_channel_of_its_own(
    virtual_time_session: ProtobufSimulationSession, watch: Callable[[str], int]
) -> None:
    first = watch(FILTERED_CURRENT)
    second = watch(LAST_TOGGLE)

    assert first >= WATCH_CHANNEL_BASE
    assert second != first
    assert len(virtual_time_session.read_variable_watches()) == 2


def test_writing_a_variable_reaches_the_firmware(
    virtual_time_session: ProtobufSimulationSession,
    watch: Callable[[str], int],
    watched_value: Callable[[int], float],
) -> None:
    """The write lands in the firmware's own memory, not in a copy.

    The example filters this value towards the measurement it reads, so it
    decays after the write instead of staying put. Decaying is the proof:
    only the firmware does that, and it only does it to its own variable.
    The bounds are loose because the example keeps running between requests,
    so how far it decayed is a matter of timing.
    """
    channel = watch(FILTERED_CURRENT)
    assert watched_value(channel) == pytest.approx(0.0)

    virtual_time_session.write_variable(channel, WRITTEN_VALUE)
    virtual_time_session.advance_time(STEP_MICROSECONDS)

    assert 0.0 < watched_value(channel) < WRITTEN_VALUE


def test_a_change_is_recorded_in_the_trace(
    virtual_time_session: ProtobufSimulationSession, watch: Callable[[str], int]
) -> None:
    channel = watch(FILTERED_CURRENT)
    # The example records its own channels far faster than a client reads,
    # so the trace is emptied first. Otherwise one read returns the oldest
    # samples it holds and the change never comes into view.
    virtual_time_session.clear_trace()

    virtual_time_session.write_variable(channel, WRITTEN_VALUE)
    virtual_time_session.advance_time(STEP_MICROSECONDS)

    samples, _ = virtual_time_session.read_trace()
    recorded = [sample.value for sample in samples if sample.channel == channel]

    assert recorded, "the watch recorded nothing"
    assert max(recorded) > 1.0


def test_a_removed_watch_stops_being_sampled(
    virtual_time_session: ProtobufSimulationSession, watch: Callable[[str], int]
) -> None:
    channel = watch(FILTERED_CURRENT)

    virtual_time_session.remove_variable_watch(channel)

    assert virtual_time_session.read_variable_watches() == ()
    with pytest.raises(SimulationRejectedError, match="no watch holds that channel"):
        virtual_time_session.remove_variable_watch(channel)


def test_an_address_outside_the_image_is_refused(
    virtual_time_session: ProtobufSimulationSession,
    variables: dict[str, FirmwareVariable],
) -> None:
    """A stale build would otherwise take the firmware down with it."""
    with pytest.raises(SimulationRejectedError, match="outside the running image"):
        virtual_time_session.watch_variable(variables[FILTERED_CURRENT], 0x1000)


def test_a_value_the_variable_cannot_hold_is_refused(
    virtual_time_session: ProtobufSimulationSession, watch: Callable[[str], int]
) -> None:
    with pytest.raises(SimulationRejectedError, match="outside the range"):
        virtual_time_session.write_variable(watch(LAST_TOGGLE), 2**40)


def test_the_addresses_a_watch_reports_are_the_relocated_ones(
    virtual_time_session: ProtobufSimulationSession,
    image: LoadedImage,
    variables: dict[str, FirmwareVariable],
) -> None:
    variable = variables[FILTERED_CURRENT]

    started = virtual_time_session.watch_variable(variable, image.runtime_address_of(variable))

    assert started.runtime_address == variable.link_time_address + image.slide


def test_the_three_programmes_in_the_executable_are_told_apart(
    variables: dict[str, FirmwareVariable],
) -> None:
    """Only one of them is the firmware, and only it is what anyone wants.

    The runtime is compiled from the package by looper-cli and from a
    checkout by CMake, so it is recognised by which translation unit
    described a variable rather than by where that unit happened to sit.
    The C runtime is recognised by having been compiled somewhere else
    entirely, years ago, on another machine.
    """
    by_origin: dict[VariableOrigin, set[str]] = {origin: set() for origin in VariableOrigin}
    for path, variable in variables.items():
        by_origin[variable.origin].add(path)

    assert FILTERED_CURRENT in by_origin[VariableOrigin.FIRMWARE]
    assert "status.led_on" in by_origin[VariableOrigin.FIRMWARE]

    simulation = by_origin[VariableOrigin.SIMULATION]
    assert simulation, "the runtime keeps state of its own"
    assert all("looper_" in str(variables[path].declared_in) for path in simulation)

    toolchain = by_origin[VariableOrigin.TOOLCHAIN]
    assert toolchain, "a process needs a C runtime to start at all"
    assert not any("looper_" in str(variables[path].declared_in) for path in toolchain)
