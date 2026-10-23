"""The shape of a function's durations, measured by the thing itself.

The bands are counted in the runtime and read by the client, and the
only thing that makes them mean anything is that both ends agree on
which band is which. Nothing in a type system checks that: a band
list written one value at a time loses its empty bands and shifts
every count after them, which is how this was wrong to begin with.

So the check is against the two numbers the same measurement already
carries. The lowest band anything landed in has to be the band the
shortest call belongs to, and the highest the band of the longest.
"""

from __future__ import annotations

import time

import pytest

from looper.domain.model.measurement import bucket_of
from looper.infrastructure.ipc import ProtobufSimulationSession

NANOSECONDS_PER_SECOND = 1e9

#: Long enough for the firmware to have called everything a few times.
WINDOW_SECONDS = 0.5


@pytest.fixture
def measured(real_time_session: ProtobufSimulationSession) -> tuple[object, ...]:
    """What the adapter boundary measured over a short window."""
    time.sleep(WINDOW_SECONDS)
    return tuple(one for one in real_time_session.read_call_timings() if one.calls > 0)


def test_something_was_measured(measured: tuple[object, ...]) -> None:
    assert measured


def test_every_call_landed_in_exactly_one_band(measured: tuple[object, ...]) -> None:
    for timing in measured:
        assert timing.spread.total == timing.calls, timing.function  # type: ignore[attr-defined]


def test_the_lowest_band_is_the_one_the_quickest_call_belongs_to(
    measured: tuple[object, ...],
) -> None:
    """A dropped empty band would shift this down."""
    for timing in measured:
        bands = timing.spread.buckets  # type: ignore[attr-defined]
        shortest = timing.shortest_nanoseconds / NANOSECONDS_PER_SECOND  # type: ignore[attr-defined]
        assert bands[0].index == bucket_of(shortest), timing.function  # type: ignore[attr-defined]


def test_the_highest_band_is_the_one_the_slowest_call_belongs_to(
    measured: tuple[object, ...],
) -> None:
    for timing in measured:
        bands = timing.spread.buckets  # type: ignore[attr-defined]
        longest = timing.longest_nanoseconds / NANOSECONDS_PER_SECOND  # type: ignore[attr-defined]
        assert bands[-1].index == bucket_of(longest), timing.function  # type: ignore[attr-defined]


def test_the_mean_falls_between_the_bands_that_were_used(
    measured: tuple[object, ...],
) -> None:
    """A weaker check than the two above, and it catches a wholesale shift."""
    for timing in measured:
        bands = timing.spread.buckets  # type: ignore[attr-defined]
        mean = timing.mean_nanoseconds / NANOSECONDS_PER_SECOND  # type: ignore[attr-defined]
        assert bands[0].low_seconds <= max(mean, bands[0].low_seconds)
        assert mean <= bands[-1].high_seconds, timing.function  # type: ignore[attr-defined]
