"""What a busy window carries, and what it only counts.

A bus exchanging seven thousand times a second fills a five second
window with thirty five thousand marks, and a row is about a
thousand pixels wide. Carrying every one of them as something to
draw cost a third of a second per reading and drew thirty marks on
every pixel, which is what made this page stop responding.

So a row carries a mark for as many as can be told apart and counts
the rest. What has to hold is that the counting, the regularity and
the spikes are of everything that happened -- a page that thinned
those as well would be quietly reporting the thinning.
"""

from __future__ import annotations

from simulation_doubles import RecordingSession

from looper.application.mapping.timeline_view import MAXIMUM_MARKS
from looper.application.queries import ObserveTimeline
from looper.domain.model.simulation import (
    BusAddress,
    BusDirection,
    BusKind,
    BusTraceEntry,
    SimulatedBus,
)

SECOND = 1_000_000
CAN = SimulatedBus(identifier=0, kind=BusKind.CAN, label="CAN1")

#: Enough to be thinned several times over.
CROWD = MAXIMUM_MARKS * 5


def an_exchange(seconds: float, sequence: int) -> BusTraceEntry:
    """One CAN frame that crossed."""
    return BusTraceEntry(
        bus=CAN.identifier,
        kind=BusKind.CAN,
        direction=BusDirection.OUTBOUND,
        address=BusAddress(BusKind.CAN, 0x702),
        payload=b"\x01",
        microseconds=int(seconds * SECOND),
        sequence=sequence,
    )


def a_busy_second(count: int = CROWD, late_at: int | None = None) -> RecordingSession:
    """A bus that crossed `count` times inside one second.

    Args:
        count: How many exchanges to record.
        late_at: Which one to delay, so that there is one gap worth
            finding among all the regular ones.
    """
    session = RecordingSession()
    session.buses = (CAN,)
    moment = 1.0
    recorded = []
    for sequence in range(count):
        moment += 0.1 if sequence == late_at else 1.0 / count
        recorded.append(an_exchange(moment, sequence))
    session.exchanges = tuple(recorded)
    return session


def a_lane(session: RecordingSession) -> object:
    """The one bus row of one reading."""
    return ObserveTimeline(session).execute().lanes[0]


def test_a_row_carries_no_more_marks_than_it_can_show() -> None:
    lane = a_lane(a_busy_second())

    assert len(lane.marks) <= MAXIMUM_MARKS  # type: ignore[attr-defined]


def test_it_still_says_how_many_there_were() -> None:
    """The count is the reading; the marks are only the drawing."""
    lane = a_lane(a_busy_second())

    assert lane.count == CROWD  # type: ignore[attr-defined]
    assert f"{CROWD}x" in lane.summary  # type: ignore[attr-defined]


def test_the_marks_are_spread_across_the_window() -> None:
    """Keeping the newest would draw a block on the right and a gap."""
    lane = a_lane(a_busy_second())
    marks = lane.marks  # type: ignore[attr-defined]

    middle = marks[len(marks) // 2].seconds
    assert marks[0].seconds < middle < marks[-1].seconds


def test_the_row_still_begins_and_ends_where_its_traffic_did() -> None:
    session = a_busy_second()
    lane = a_lane(session)

    assert lane.marks[-1].seconds == session.exchanges[-1].seconds  # type: ignore[attr-defined]


def test_the_one_late_arrival_survives_the_thinning() -> None:
    """It is the whole reason for drawing the gaps at all."""
    lane = a_lane(a_busy_second(late_at=CROWD // 2))

    assert lane.worst_gap_seconds > 0.09  # type: ignore[attr-defined]
    assert max(gap for _, gap in lane.gaps) > 0.09  # type: ignore[attr-defined]


def test_the_usual_gap_is_not_dragged_by_the_late_one() -> None:
    """Which is why it is the median and not the mean."""
    lane = a_lane(a_busy_second(late_at=CROWD // 2))

    assert lane.usual_gap_seconds < 0.001  # type: ignore[attr-defined]


def test_a_quiet_row_carries_everything_it_had() -> None:
    """Thinning is what a busy row needs and a quiet one must not get."""
    lane = a_lane(a_busy_second(count=12))

    assert len(lane.marks) == 12  # type: ignore[attr-defined]
    assert lane.count == 12  # type: ignore[attr-defined]


def test_the_gaps_handed_over_are_fewer_than_the_gaps_there_were() -> None:
    """A thousand columns is what a row has; the rest land on top."""
    lane = a_lane(a_busy_second())

    assert 0 < len(lane.gaps) < lane.count  # type: ignore[attr-defined]
