"""How a measured time was spread, rather than what it averaged.

The three shapes a firmware produces all average the same: one narrow
hump, two humps, and one hump with a long tail. Every property here
exists so that a reader can tell them apart, and the tests are
written as those three shapes.
"""

from __future__ import annotations

import pytest

from looper.domain.model.measurement import (
    BUCKET_COUNT,
    Bucket,
    Distribution,
    bucket_of,
    distribute,
)

MICROSECOND = 1e-6
MILLISECOND = 1e-3


def test_a_duration_falls_in_the_band_of_its_power_of_two() -> None:
    assert bucket_of(1e-9) == 0
    assert bucket_of(2e-9) == 1
    assert bucket_of(1023e-9) == 9
    assert bucket_of(1024e-9) == 10


def test_nothing_measurable_falls_in_the_first_band() -> None:
    assert bucket_of(0.0) == 0
    assert bucket_of(-1.0) == 0


def test_anything_slower_than_the_last_band_lands_in_it() -> None:
    """Past four seconds the exact figure is not the detail."""
    assert bucket_of(60.0) == BUCKET_COUNT - 1


def test_a_band_says_what_it_holds() -> None:
    band = Bucket(index=10, count=3)

    assert band.low_seconds == pytest.approx(1024e-9)
    assert band.high_seconds == pytest.approx(2048e-9)


def test_one_narrow_hump_is_one_band_wide() -> None:
    """A call that does one thing, always the same way."""
    spread = distribute([1.1 * MICROSECOND] * 100)

    assert spread.span == 1
    assert not spread.is_split
    assert spread.busiest is not None
    assert spread.busiest.count == 100


def test_two_humps_are_told_from_one_wide_one() -> None:
    """Two paths through the code, and something choosing between them."""
    split = distribute([1.0 * MICROSECOND] * 50 + [1.0 * MILLISECOND] * 50)
    wide = distribute([(1 << step) * 1e-9 for step in range(10, 20) for _ in range(10)])

    assert split.is_split
    assert not wide.is_split


def test_a_long_tail_shows_in_the_span_and_not_in_the_bulk() -> None:
    """Usually fine, occasionally blocks: the one that breaks a deadline."""
    spread = distribute([1.0 * MICROSECOND] * 999 + [100.0 * MILLISECOND])

    assert spread.busiest is not None
    assert spread.busiest.high_seconds < 4 * MICROSECOND
    assert spread.span > 15


def test_a_share_is_reported_as_what_it_came_in_under() -> None:
    """An upper bound, which is the number worth quoting."""
    spread = distribute([1.0 * MICROSECOND] * 99 + [100.0 * MILLISECOND])

    assert spread.at_most_seconds(0.9) < 4 * MICROSECOND
    assert spread.at_most_seconds(1.0) > 50 * MILLISECOND


def test_nothing_measured_reports_nothing() -> None:
    empty = Distribution()

    assert not empty.is_measured
    assert empty.total == 0
    assert empty.span == 0
    assert empty.busiest is None
    assert empty.at_most_seconds(0.5) == 0.0


def test_only_the_bands_that_hold_something_are_listed() -> None:
    spread = distribute([1.0 * MICROSECOND] * 5)

    assert len(spread.buckets) == 1


def test_a_band_cannot_hold_a_negative_count() -> None:
    with pytest.raises(ValueError, match="negative number"):
        Distribution((1, -2))


def test_every_measurement_is_counted_once() -> None:
    spread = distribute([1.0 * MICROSECOND, 2.0 * MILLISECOND, 0.0])

    assert spread.total == 3
