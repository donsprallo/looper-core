"""The stretch of time every lane of a timeline agrees on.

Panning and zooming look like arithmetic and are mostly edge cases: a
zoom that moves what you were looking at, a pan that runs off the end
of the recording, a window narrower than the clock can resolve. Each
of those is a plot that misleads rather than one that breaks, so each
is pinned down here.
"""

from __future__ import annotations

import pytest

from looper.domain.model.timeline import SHORTEST_SECONDS, TimeWindow

RECORDING = TimeWindow(0.0, 10.0)


def test_a_window_knows_how_long_it_is() -> None:
    assert TimeWindow(2.0, 5.0).duration_seconds == pytest.approx(3.0)
    assert TimeWindow(2.0, 5.0).middle_seconds == pytest.approx(3.5)


def test_a_window_that_ends_before_it_begins_is_refused() -> None:
    with pytest.raises(ValueError, match="ends after it begins"):
        TimeWindow(5.0, 2.0)


def test_a_window_of_no_width_is_refused() -> None:
    with pytest.raises(ValueError, match="ends after it begins"):
        TimeWindow(1.0, 1.0)


def test_a_window_narrower_than_the_clock_is_allowed() -> None:
    """A rule nobody can keep is worse than none.

    A recording running long enough puts the moments past the point
    where a float tells one microsecond from the next, and refusing
    those windows would refuse the recording rather than the window.
    """
    assert TimeWindow(1.0, 1.0 + SHORTEST_SECONDS / 2.0).duration_seconds > 0.0


def test_a_moment_far_into_a_run_still_makes_a_window() -> None:
    """Eleven days in, a microsecond is below what the number can hold."""
    far = 1e6

    spanning = TimeWindow.spanning([far])

    assert spanning is not None
    assert spanning.duration_seconds > 0.0


def test_zooming_in_as_far_as_it_goes_still_leaves_a_window() -> None:
    narrowed = TimeWindow(0.0, 1.0)
    for _ in range(100):
        narrowed = narrowed.zoomed(0.01)

    assert narrowed.duration_seconds > 0.0


def test_both_ends_belong_to_the_window() -> None:
    """So that an event exactly on the boundary is drawn, not lost."""
    window = TimeWindow(2.0, 5.0)

    assert window.holds(2.0)
    assert window.holds(5.0)
    assert not window.holds(5.000001)


def test_windows_that_touch_overlap() -> None:
    assert TimeWindow(0.0, 2.0).overlaps(TimeWindow(2.0, 4.0))
    assert not TimeWindow(0.0, 2.0).overlaps(TimeWindow(2.5, 4.0))


def test_zooming_in_halves_what_is_shown() -> None:
    zoomed = TimeWindow(0.0, 10.0).zoomed(0.5)

    assert zoomed.duration_seconds == pytest.approx(5.0)
    assert zoomed.middle_seconds == pytest.approx(5.0)


def test_zooming_keeps_the_moment_it_was_asked_about_where_it_was() -> None:
    """A zoom that moves the cursor is a zoom you have to undo."""
    zoomed = TimeWindow(0.0, 10.0).zoomed(0.5, around_seconds=2.0)

    assert zoomed.start_seconds == pytest.approx(1.0)
    assert zoomed.end_seconds == pytest.approx(6.0)
    assert zoomed.holds(2.0)


def test_zooming_out_widens_about_the_same_moment() -> None:
    zoomed = TimeWindow(4.0, 6.0).zoomed(2.0, around_seconds=5.0)

    assert zoomed == TimeWindow(3.0, 7.0)


def test_a_zoom_factor_has_to_be_positive() -> None:
    with pytest.raises(ValueError, match="zoom factor is positive"):
        TimeWindow(0.0, 1.0).zoomed(0.0)


def test_moving_a_window_keeps_its_length() -> None:
    moved = TimeWindow(1.0, 3.0).moved_by(4.0)

    assert moved == TimeWindow(5.0, 7.0)


def test_panning_past_the_end_stops_at_the_end() -> None:
    """Pushed back inside, not cut short: what is on screen stays as wide."""
    clamped = TimeWindow(9.0, 12.0).clamped_to(RECORDING)

    assert clamped.duration_seconds == pytest.approx(3.0)
    assert clamped == TimeWindow(7.0, 10.0)


def test_panning_before_the_start_stops_at_the_start() -> None:
    clamped = TimeWindow(-5.0, -2.0).clamped_to(RECORDING)

    assert clamped == TimeWindow(0.0, 3.0)


def test_a_window_already_inside_is_left_alone() -> None:
    assert TimeWindow(2.0, 5.0).clamped_to(RECORDING) == TimeWindow(2.0, 5.0)


def test_a_window_wider_than_the_recording_becomes_the_recording() -> None:
    assert TimeWindow(-10.0, 30.0).clamped_to(RECORDING) == RECORDING


def test_a_window_spans_the_moments_it_was_given() -> None:
    spanning = TimeWindow.spanning([3.0, 1.0, 7.5])

    assert spanning == TimeWindow(1.0, 7.5)


def test_one_moment_still_makes_a_window_something_can_be_drawn_in() -> None:
    spanning = TimeWindow.spanning([4.0])

    assert spanning is not None
    assert spanning.start_seconds == pytest.approx(4.0)
    assert spanning.duration_seconds == pytest.approx(SHORTEST_SECONDS)


def test_no_moments_make_no_window_at_all() -> None:
    """Not a window of length zero: the caller has to decide what to show."""
    assert TimeWindow.spanning([]) is None
