"""When the pins changed, measured against a firmware that toggles one.

The pin model says what a pin is now, and a snapshot taken on a poll
sees whatever it happens to see. What the recording has to do is
catch every change between two polls, because the question it exists
for -- did this edge come before that one -- is lost the moment one
of them is missed.

Blinky is the honest test for it: its LED toggles on a schedule it
sets itself, so the stretches have a length nobody told the client.
"""

from __future__ import annotations

import time

import pytest

from looper.application.queries import ObserveTimeline
from looper.domain.model.simulation import SignalLevel
from looper.infrastructure.ipc import ProtobufSimulationSession

#: Long enough for the example to toggle a few times.
WINDOW_SECONDS = 2.2

#: What the example's LED period is, as its own source sets it.
EXPECTED_STRETCH_SECONDS = 0.5


@pytest.fixture
def recorded(real_time_session: ProtobufSimulationSession) -> tuple[object, ...]:
    """Every change the simulation recorded over a couple of seconds."""
    time.sleep(WINDOW_SECONDS)
    changes, _ = real_time_session.read_pin_trace()
    return changes


def test_the_firmware_toggling_a_pin_is_recorded(recorded: tuple[object, ...]) -> None:
    assert len(recorded) > 2


def test_every_change_is_a_change(recorded: tuple[object, ...]) -> None:
    """A pin read a thousand times without moving is not a thousand events."""
    for pin in {one.pin for one in recorded}:  # type: ignore[attr-defined]
        levels = [one.level for one in recorded if one.pin == pin]  # type: ignore[attr-defined]
        assert all(
            earlier is not later for earlier, later in zip(levels, levels[1:], strict=False)
        ), pin


def test_a_pin_starts_at_a_known_level(recorded: tuple[object, ...]) -> None:
    """Registration records it, so a row has somewhere to begin."""
    assert recorded[0].microseconds >= 0  # type: ignore[attr-defined]
    assert recorded[0].level in (SignalLevel.HIGH, SignalLevel.LOW)  # type: ignore[attr-defined]


def test_the_stretches_are_the_length_the_firmware_chose(
    recorded: tuple[object, ...],
) -> None:
    """Nobody told the client half a second; the firmware did it."""
    toggling = _busiest_pin(recorded)
    moments = [one.seconds for one in recorded if one.pin == toggling]  # type: ignore[attr-defined]
    gaps = [later - earlier for earlier, later in zip(moments, moments[1:], strict=False)]

    assert gaps
    assert all(gap == pytest.approx(EXPECTED_STRETCH_SECONDS, abs=0.1) for gap in gaps[1:]), gaps


def test_the_timeline_turns_the_changes_into_stretches(
    real_time_session: ProtobufSimulationSession,
) -> None:
    timeline = ObserveTimeline(real_time_session, window_seconds=3.0)
    for _ in range(4):
        time.sleep(0.4)
        view = timeline.execute()

    rows = [lane for lane in view.lanes if lane.kind == "digital"]
    assert rows
    assert all(mark.duration_seconds > 0.0 for row in rows for mark in row.marks)


def _busiest_pin(recorded: tuple[object, ...]) -> int:
    """The pin that changed most, which is the one being toggled."""
    pins = [one.pin for one in recorded]  # type: ignore[attr-defined]
    return max(set(pins), key=pins.count)
