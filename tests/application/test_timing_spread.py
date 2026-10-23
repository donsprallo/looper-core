"""The shape of a function's durations, on its way to the chart.

What the runtime counts is bands; what a reader needs beside a bar is
a sentence. The one worth getting right is the function with two
separated groups, because that is two paths through the code rather
than one with variation, and no average will ever say so.
"""

from __future__ import annotations

from looper.application.mapping.timing_view import build_timing_report_view
from looper.domain.model.measurement import BUCKET_COUNT, Distribution, distribute
from looper.domain.model.simulation import CallTiming

MICROSECOND = 1e-6
MILLISECOND = 1e-3


def a_timing(spread: Distribution, function: str = "adapter_spi_transfer") -> CallTiming:
    """One measured function with the given shape."""
    return CallTiming(
        function=function,
        calls=spread.total,
        answered_calls=spread.total,
        total_nanoseconds=1000,
        shortest_nanoseconds=1,
        longest_nanoseconds=100,
        spread=spread,
    )


def test_the_bands_reach_the_view_in_order() -> None:
    """Their position is what says which band a count belongs to."""
    spread = distribute([1.0 * MICROSECOND] * 7)

    view = build_timing_report_view((a_timing(spread),))

    assert len(view.entries[0].bands) == BUCKET_COUNT
    assert sum(view.entries[0].bands) == 7
    assert view.entries[0].is_spread_known


def test_a_typical_duration_is_quoted_as_an_upper_bound() -> None:
    spread = distribute([1.0 * MICROSECOND] * 100)

    view = build_timing_report_view((a_timing(spread),))

    assert "95% under" in view.entries[0].shape


def test_two_separated_groups_are_named_as_two_paths() -> None:
    """The finding no average carries."""
    spread = distribute([1.0 * MICROSECOND] * 50 + [1.0 * MILLISECOND] * 50)

    view = build_timing_report_view((a_timing(spread),))

    assert view.entries[0].shape.startswith("two paths")


def test_one_wide_hump_is_not_called_two_paths() -> None:
    spread = distribute([(1 << step) * 1e-9 for step in range(10, 20) for _ in range(5)])

    view = build_timing_report_view((a_timing(spread),))

    assert "two paths" not in view.entries[0].shape


def test_a_measurement_with_no_bands_says_nothing_about_its_shape() -> None:
    """An older simulation counts no bands, and inventing one would lie."""
    view = build_timing_report_view((a_timing(Distribution()),))

    assert view.entries[0].shape == ""
    assert not view.entries[0].is_spread_known
