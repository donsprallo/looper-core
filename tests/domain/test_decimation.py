"""What survives when a trace is cut down to the width of the plot.

The point of reducing is speed, and the price must not be the thing being
looked for. A spike between two drawn samples is usually exactly that, so
each column keeps its extremes: the reduced trace spans what the full one
spans, and the axis computed from it is the same axis.
"""

from __future__ import annotations

import math

import pytest

from looper.domain.services.decimation import decimate, value_range

WINDOW = 1.0
COLUMNS = 100


def a_ramp(count: int) -> list[tuple[float, float]]:
    """Points rising steadily across one window."""
    return [(index / count * WINDOW, float(index)) for index in range(count)]


def test_a_short_trace_is_left_alone() -> None:
    """Below a couple of points per column there is nothing to gain."""
    points = a_ramp(20)

    assert decimate(points, 0.0, WINDOW, COLUMNS) == points


def test_a_long_trace_is_cut_to_about_two_points_per_column() -> None:
    reduced = decimate(a_ramp(10_000), 0.0, WINDOW, COLUMNS)

    assert len(reduced) <= COLUMNS * 2


def test_the_extremes_of_the_window_survive() -> None:
    """The axis is computed from what is drawn, so it has to span the same."""
    points = a_ramp(10_000)

    reduced = decimate(points, 0.0, WINDOW, COLUMNS)

    assert value_range(reduced) == value_range(points)


def test_a_spike_between_samples_is_not_lost() -> None:
    points = [(index / 10_000 * WINDOW, 0.0) for index in range(10_000)]
    points[5_000] = (points[5_000][0], 42.0)

    reduced = decimate(points, 0.0, WINDOW, COLUMNS)

    assert value_range(reduced) == (0.0, 42.0)
    assert (points[5_000][0], 42.0) in reduced


def test_a_dip_between_samples_is_not_lost_either() -> None:
    points = [(index / 10_000 * WINDOW, 1.0) for index in range(10_000)]
    points[5_000] = (points[5_000][0], -7.0)

    assert value_range(decimate(points, 0.0, WINDOW, COLUMNS)) == (-7.0, 1.0)


def test_points_stay_in_the_order_they_were_sampled() -> None:
    """A polyline drawn out of order would cross itself."""
    points = [(index / 10_000 * WINDOW, math.sin(index / 400.0)) for index in range(10_000)]

    reduced = decimate(points, 0.0, WINDOW, COLUMNS)

    assert all(earlier[0] <= later[0] for earlier, later in zip(reduced, reduced[1:], strict=False))


def test_a_plot_with_no_width_draws_what_it_was_given() -> None:
    points = a_ramp(10_000)

    assert decimate(points, 0.0, WINDOW, 0) == points
    assert decimate(points, 0.0, 0.0, COLUMNS) == points


def test_a_column_holding_one_point_keeps_it_once() -> None:
    """Two copies of the same point would double every flat stretch."""
    points = [(index / 200 * WINDOW, 1.0) for index in range(200)]

    reduced = decimate(points, 0.0, WINDOW, COLUMNS)

    assert len(reduced) == len(set(reduced))


def test_an_empty_trace_has_no_range() -> None:
    assert value_range([]) is None


def test_a_range_is_the_lowest_and_the_highest() -> None:
    assert value_range([(0.0, 3.0), (1.0, -2.0), (2.0, 7.0)]) == (-2.0, 7.0)


def test_reducing_is_much_faster_than_drawing_everything() -> None:
    """The reason this exists, kept honest as a test rather than a comment."""
    points = a_ramp(40_000)

    reduced = decimate(points, 0.0, WINDOW, 1000)

    assert len(reduced) < len(points) / 10
    assert value_range(reduced) == pytest.approx(value_range(points))
