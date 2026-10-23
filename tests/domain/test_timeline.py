"""Lanes, the things on them, and what a window shows of both.

The arrangement is most of the value: three recordings that already
share a clock, put on one ruler. What has to hold is that nothing
moves when you pan -- an event on the boundary stays drawn, a long
one that started off screen stays drawn, and a lane with nothing in
view stays a lane.
"""

from __future__ import annotations

import pytest

from looper.domain.model.timeline import (
    LaneKind,
    Timeline,
    TimelineEvent,
    TimelineLane,
    TimeWindow,
)

WINDOW = TimeWindow(2.0, 4.0)


def an_event(seconds: float, duration_seconds: float = 0.0) -> TimelineEvent:
    """One thing that happened, named after when."""
    return TimelineEvent(seconds=seconds, label=f"at {seconds}", duration_seconds=duration_seconds)


def a_lane(key: str, *moments: float) -> TimelineLane:
    """A lane of instants."""
    return TimelineLane(
        key=key, label=key, kind=LaneKind.CALL, events=tuple(an_event(one) for one in moments)
    )


def test_an_instant_is_told_from_a_stretch() -> None:
    """A bar of no width is a bar nobody can click on."""
    assert an_event(1.0).is_instant
    assert not an_event(1.0, duration_seconds=0.5).is_instant
    assert an_event(1.0, duration_seconds=0.5).end_seconds == pytest.approx(1.5)


def test_an_event_cannot_last_a_negative_time() -> None:
    with pytest.raises(ValueError, match="cannot last"):
        TimelineEvent(seconds=1.0, label="spi", duration_seconds=-0.1)


def test_an_event_inside_the_window_is_shown() -> None:
    assert an_event(3.0).falls_within(WINDOW)


def test_an_event_on_the_boundary_is_shown() -> None:
    assert an_event(2.0).falls_within(WINDOW)
    assert an_event(4.0).falls_within(WINDOW)


def test_an_event_outside_is_not() -> None:
    assert not an_event(1.9).falls_within(WINDOW)
    assert not an_event(4.1).falls_within(WINDOW)


def test_a_stretch_that_began_before_the_window_is_still_shown() -> None:
    """Hiding those would hide exactly the long ones."""
    assert an_event(1.0, duration_seconds=2.0).falls_within(WINDOW)


def test_a_stretch_that_covers_the_whole_window_is_shown() -> None:
    assert an_event(0.0, duration_seconds=10.0).falls_within(WINDOW)


def test_a_lane_keeps_its_events_in_order() -> None:
    with pytest.raises(ValueError, match="not in order"):
        TimelineLane(
            key="can", label="CAN", kind=LaneKind.BUS, events=(an_event(2.0), an_event(1.0))
        )


def test_a_lane_without_a_key_is_refused() -> None:
    with pytest.raises(ValueError, match="identified by a key"):
        TimelineLane(key="", label="CAN", kind=LaneKind.BUS)


def test_a_lane_with_no_traffic_says_so() -> None:
    """A bus with no traffic is a finding; a bus nobody wired up is another."""
    assert a_lane("can").is_empty
    assert not a_lane("can", 1.0).is_empty


def test_a_lane_hands_over_its_moments_for_asking_about_regularity() -> None:
    assert a_lane("can", 1.0, 2.0, 3.0).moments == (1.0, 2.0, 3.0)


def test_a_window_narrows_a_lane_to_what_it_shows() -> None:
    narrowed = a_lane("can", 1.0, 3.0, 5.0).within(WINDOW)

    assert narrowed.moments == (3.0,)
    assert narrowed.key == "can"


def test_two_lanes_cannot_share_a_key() -> None:
    with pytest.raises(ValueError, match="cannot share a key"):
        Timeline((a_lane("can", 1.0), a_lane("can", 2.0)))


def test_a_timeline_spans_everything_on_every_lane() -> None:
    timeline = Timeline((a_lane("can", 1.0, 4.0), a_lane("spi", 0.5, 9.0)))

    assert timeline.recorded == TimeWindow(0.5, 9.0)


def test_a_timeline_with_nothing_recorded_spans_nothing() -> None:
    timeline = Timeline((a_lane("can"), a_lane("spi")))

    assert timeline.is_empty
    assert timeline.recorded is None


def test_a_lane_with_nothing_in_view_is_still_a_lane() -> None:
    """A row that vanishes makes the rows below it jump."""
    timeline = Timeline((a_lane("can", 3.0), a_lane("spi", 9.0)))

    shown = timeline.within(WINDOW)

    assert [lane.key for lane in shown.lanes] == ["can", "spi"]
    assert shown.lane("spi") is not None
    assert shown.lane("spi").is_empty  # type: ignore[union-attr]


def test_a_lane_carries_detail_for_fewer_than_it_counts() -> None:
    """A busy row draws a mark per pixel and counts every occurrence."""
    lane = TimelineLane(
        key="bus:0",
        label="CAN1",
        kind=LaneKind.BUS,
        events=(an_event(1.0), an_event(3.0)),
        moments=(1.0, 1.5, 2.0, 2.5, 3.0),
    )

    assert lane.is_thinned
    assert len(lane.moments) == 5
    assert not lane.is_empty


def test_a_lane_told_nothing_of_its_moments_takes_them_from_its_events() -> None:
    """Which is every row but a busy one."""
    lane = a_lane("call:spi", 1.0, 2.0, 3.0)

    assert lane.moments == (1.0, 2.0, 3.0)
    assert not lane.is_thinned


def test_a_window_narrows_what_a_thinned_lane_counts() -> None:
    lane = TimelineLane(
        key="bus:0",
        label="CAN1",
        kind=LaneKind.BUS,
        events=(an_event(3.0),),
        moments=(1.0, 3.0, 9.0),
    )

    assert lane.within(WINDOW).moments == (3.0,)


def test_moments_that_run_backwards_are_refused() -> None:
    """A row out of order draws nonsense and measures a negative gap."""
    with pytest.raises(ValueError, match="not in order"):
        TimelineLane(key="bus:0", label="CAN1", kind=LaneKind.BUS, moments=(3.0, 1.0))


def test_a_lane_can_be_found_by_key() -> None:
    timeline = Timeline((a_lane("can", 1.0),))

    assert timeline.lane("can") is not None
    assert timeline.lane("uart") is None
