"""The stretches a pin spent at one level.

Two ends decide whether a logic analyser is honest. The last run has
no change to close it and must reach the edge of what is shown, or a
signal that is still high looks like one that stopped. The first has
no change to open it, and the time before anything was recorded is
not time the pin spent low -- it is time nobody watched it.
"""

from __future__ import annotations

import pytest

from looper.domain.model.simulation import PinChange, SignalLevel
from looper.domain.services import LevelRun, runs_of

SECOND = 1_000_000


def a_change(seconds: float, high: bool, sequence: int = 0) -> PinChange:
    """One level the pin took."""
    return PinChange(
        pin=3,
        level=SignalLevel.HIGH if high else SignalLevel.LOW,
        microseconds=int(seconds * SECOND),
        sequence=sequence,
    )


def test_each_change_begins_a_run_that_the_next_one_ends() -> None:
    runs = runs_of([a_change(1.0, True), a_change(1.5, False), a_change(2.0, True)], 3.0)

    assert [one.is_high for one in runs] == [True, False, True]
    assert runs[0].start_seconds == 1.0
    assert runs[0].end_seconds == 1.5
    assert runs[0].duration_seconds == pytest.approx(0.5)


def test_the_last_run_reaches_the_edge_of_what_is_shown() -> None:
    """Otherwise a signal that is still high looks like one that stopped."""
    runs = runs_of([a_change(1.0, True)], until_seconds=5.0)

    assert runs[-1].end_seconds == 5.0
    assert runs[-1].is_open


def test_only_the_last_run_is_open() -> None:
    runs = runs_of([a_change(1.0, True), a_change(2.0, False)], 5.0)

    assert [one.is_open for one in runs] == [False, True]


def test_a_pin_that_never_changed_has_no_runs() -> None:
    """Nothing known is not the same as low, and is not drawn as low."""
    assert runs_of([], until_seconds=5.0) == ()


def test_the_last_run_is_not_dragged_backwards() -> None:
    """A window that ends before the last change still shows it."""
    runs = runs_of([a_change(9.0, True)], until_seconds=5.0)

    assert runs[-1].end_seconds == 9.0
    assert runs[-1].duration_seconds == 0.0


def test_a_run_cannot_end_before_it_begins() -> None:
    with pytest.raises(ValueError, match="no earlier than it begins"):
        LevelRun(level=SignalLevel.HIGH, start_seconds=2.0, end_seconds=1.0)
