"""What a measurement at the adapter boundary says.

Two questions in one record. What the call cost, which is host time and
nothing more; and how often anything answered it, which is the difference
between a simulation that implements something and one that hands the
firmware a zero and lets it believe it.
"""

from __future__ import annotations

import pytest

from looper.domain.model.simulation import CallTiming


def a_timing(**changes: object) -> CallTiming:
    """One measured function, with whatever the test wants changed."""
    fields: dict[str, object] = {
        "function": "adapter_spi_transfer_blocking",
        "calls": 100,
        "answered_calls": 100,
        "total_nanoseconds": 500_000,
        "shortest_nanoseconds": 2_000,
        "longest_nanoseconds": 90_000,
    }
    fields.update(changes)
    return CallTiming(**fields)  # type: ignore[arg-type]


def test_the_mean_is_the_total_over_the_calls() -> None:
    assert a_timing().mean_nanoseconds == pytest.approx(5_000.0)


def test_a_function_never_called_has_no_mean_rather_than_an_error() -> None:
    assert a_timing(calls=0, answered_calls=0, total_nanoseconds=0).mean_nanoseconds == 0.0


def test_a_call_nothing_answers_is_the_thing_to_look_at() -> None:
    silent = a_timing(answered_calls=0)

    assert silent.is_never_answered
    assert silent.unanswered_calls == 100
    assert not silent.is_partly_answered


def test_a_call_everything_answers_is_not_flagged() -> None:
    assert not a_timing().is_never_answered
    assert a_timing().unanswered_calls == 0


def test_a_hook_that_appeared_part_way_through_shows_as_partly_answered() -> None:
    """A device model installed late, which is worth seeing rather than hiding."""
    assert a_timing(answered_calls=40).is_partly_answered


def test_more_answers_than_calls_is_refused() -> None:
    with pytest.raises(ValueError, match="more than were made"):
        a_timing(calls=3, answered_calls=4)


def test_a_duration_is_shown_in_the_unit_that_reads() -> None:
    def one_call_of(nanoseconds: int) -> CallTiming:
        return a_timing(calls=1, answered_calls=1, total_nanoseconds=nanoseconds)

    assert one_call_of(400).display_mean == "400 ns"
    assert one_call_of(4_500).display_mean == "4.5 us"
    assert one_call_of(4_500_000).display_mean == "4.50 ms"


def test_the_worst_call_is_reported_beside_the_average() -> None:
    """A mean of microseconds hides a call that once took two hundred."""
    assert a_timing(longest_nanoseconds=201_200).display_longest == "201.2 us"


def test_the_total_is_offered_in_seconds_for_a_chart() -> None:
    assert a_timing(total_nanoseconds=2_500_000_000).total_seconds == pytest.approx(2.5)
