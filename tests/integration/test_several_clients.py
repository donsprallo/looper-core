"""Several clients on one simulation.

Two windows open at once is the ordinary case, and before this the
second one simply hung. What has to hold is that every client is
answered, that they see one simulation rather than one each, and that
one of them leaving takes nothing with it.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import connect, start_simulation

from looper.domain.model.simulation import SignalLevel
from looper.infrastructure.ipc import ProtobufSimulationSession

CLIENTS = 4


@pytest.fixture
def several(simulation_executable: Path) -> Iterator[tuple[ProtobufSimulationSession, ...]]:
    """Four sessions against one simulation."""
    process, port = start_simulation(simulation_executable)
    sessions = tuple(connect(port) for _ in range(CLIENTS))
    try:
        yield sessions
    finally:
        for session in sessions:
            session.close()
        process.terminate()
        process.wait(timeout=10.0)


def test_every_client_is_answered(
    several: tuple[ProtobufSimulationSession, ...],
) -> None:
    assert [session.firmware_name for session in several] == ["blinky"] * CLIENTS


def test_they_are_all_looking_at_one_simulation(
    several: tuple[ProtobufSimulationSession, ...],
) -> None:
    first, second = several[0], several[1]

    assert [pin.identifier for pin in first.read_gpio_pins()] == [
        pin.identifier for pin in second.read_gpio_pins()
    ]


def test_what_one_client_drives_the_others_see(
    several: tuple[ProtobufSimulationSession, ...],
) -> None:
    """One state, and every client acts on it. That is the arrangement."""
    first, second = several[0], several[1]
    inputs = [pin for pin in first.read_gpio_pins() if pin.is_drivable_by_client]
    if not inputs:
        pytest.skip("the example has no input pin to drive")
    target = inputs[0]
    wanted = SignalLevel.LOW if target.level is SignalLevel.HIGH else SignalLevel.HIGH

    first.drive_input_pin(target.identifier, wanted)

    seen = {pin.identifier: pin.level for pin in second.read_gpio_pins()}
    assert seen[target.identifier] is wanted


def test_each_client_reads_the_trace_at_its_own_pace(
    several: tuple[ProtobufSimulationSession, ...],
) -> None:
    """Where a client has read up to is the one thing it keeps to itself."""
    first, second = several[0], several[1]

    _, after_first = first.read_trace(0)
    samples, _ = second.read_trace(0)

    assert after_first > 0
    assert samples, "the second client got nothing of its own"


def test_one_client_leaving_takes_nothing_with_it(
    several: tuple[ProtobufSimulationSession, ...],
) -> None:
    first, second = several[0], several[1]

    first.close()

    assert second.read_time().microseconds > 0


def test_the_place_a_client_leaves_can_be_taken_again(
    simulation_executable: Path,
) -> None:
    process, port = start_simulation(simulation_executable)
    try:
        opened = [connect(port) for _ in range(CLIENTS)]
        for session in opened:
            session.close()
        again = connect(port)
        assert again.firmware_name == "blinky"
        again.close()
    finally:
        process.terminate()
        process.wait(timeout=10.0)
