"""How regularly something happened, out of moments already recorded.

The reason this exists in its own right: a mean period says a frame
went out every ten milliseconds and says nothing about the one that
took twenty-three. Every property here is chosen so that the single
excursion survives into the answer rather than being averaged away.
"""

from __future__ import annotations

import pytest

from looper.domain.services import Cadence, cadence_of, intervals_between

#: Ten a second, on the dot.
STEADY = (0.0, 0.1, 0.2, 0.3, 0.4)

#: The same, with one occurrence arriving late.
ONE_LATE = (0.0, 0.1, 0.2, 0.43, 0.53)


def test_the_gaps_are_one_fewer_than_the_moments() -> None:
    """So the nth gap can be plotted against the nth moment."""
    assert intervals_between(STEADY) == pytest.approx((0.1, 0.1, 0.1, 0.1))


def test_a_steady_thing_has_no_jitter() -> None:
    cadence = cadence_of(STEADY)

    assert cadence.is_measured
    assert cadence.jitter_seconds == pytest.approx(0.0, abs=1e-12)
    assert cadence.frequency_hz == pytest.approx(10.0)


def test_one_late_occurrence_shows_up_as_jitter() -> None:
    """The whole point: it is in the spread, not in the average."""
    cadence = cadence_of(ONE_LATE)

    assert cadence.longest_seconds == pytest.approx(0.23)
    assert cadence.jitter_seconds == pytest.approx(0.13)


def test_the_median_stays_put_while_the_mean_is_dragged() -> None:
    """Far apart means it went wrong rarely, rather than everywhere."""
    cadence = cadence_of(ONE_LATE)

    assert cadence.median_seconds == pytest.approx(0.1)
    assert cadence.mean_seconds > cadence.median_seconds


def test_the_gaps_that_were_too_long_are_named_by_position() -> None:
    """A reader is taken to the moment, not told a count."""
    cadence = cadence_of(ONE_LATE)

    assert cadence.late_by(0.15) == (2,)
    assert cadence.late_by(0.5) == ()


def test_one_occurrence_has_no_period_and_claims_none() -> None:
    cadence = cadence_of((1.0,))

    assert not cadence.is_measured
    assert cadence.count == 0
    assert cadence.frequency_hz == 0.0
    assert cadence.jitter_seconds == 0.0


def test_nothing_recorded_reports_nothing() -> None:
    assert not cadence_of(()).is_measured


def test_moments_do_not_run_backwards() -> None:
    with pytest.raises(ValueError, match="do not run backwards"):
        Cadence((0.1, -0.2))
