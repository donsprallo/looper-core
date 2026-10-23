"""Two readers filling one window, and what that costs to get wrong.

The measured values and the bus exchanges are read once a poll for
the scope and the bus table, and the timeline keeps a window of the
same records. Decoding them a second time cost more than everything
else that page does, so the pages are handed over instead.

That makes two sources for one window, each counting from where it
had got to: the poll, which has been reading since the client
started, and the one catching-up read when the tab is opened. They
overlap, and a window that took the overlap twice held its moments
out of order -- which the domain refuses, so the page stopped
rather than drew something wrong.
"""

from __future__ import annotations

from simulation_doubles import RecordingSession

from looper.application.queries import ObserveTimeline, ReadBusTrace, ReadTrace
from looper.domain.model.simulation import (
    AnalogChannel,
    AnalogSample,
    BusAddress,
    BusDirection,
    BusKind,
    BusTraceEntry,
    ChannelDirection,
    SimulatedBus,
)

SECOND = 1_000_000
CAN = SimulatedBus(identifier=0, kind=BusKind.CAN, label="CAN1")
POWER = AnalogChannel(
    identifier=2, label="POWER", unit="W", direction=ChannelDirection.OUTPUT, value=1.0
)


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


def a_sample(seconds: float, sequence: int) -> AnalogSample:
    """One recorded value of the power channel."""
    return AnalogSample(
        channel=POWER.identifier,
        microseconds=int(seconds * SECOND),
        value=float(sequence),
        sequence=sequence,
    )


def a_session() -> RecordingSession:
    """A simulation holding three exchanges and three values."""
    session = RecordingSession()
    session.buses = (CAN,)
    session.channels = (POWER,)
    session.exchanges = tuple(an_exchange(1.0 + one, one) for one in range(3))
    session.samples = tuple(a_sample(1.0 + one, one) for one in range(3))
    return session


def test_a_page_already_held_is_not_held_again() -> None:
    """The catch-up and the poll overlap; the window must not double."""
    session = a_session()
    timeline = ObserveTimeline(session)
    timeline.collect()

    timeline.collect_given(ReadTrace(session).execute(0), ReadBusTrace(session).execute(0))

    assert timeline.arrange().lanes[0].count == 3


def test_what_is_handed_over_after_a_catch_up_still_counts() -> None:
    """Only the overlap is dropped, not the page it arrived in."""
    session = a_session()
    timeline = ObserveTimeline(session)
    timeline.collect()
    session.exchanges = (*session.exchanges, an_exchange(4.0, 3))

    timeline.collect_given(ReadTrace(session).execute(0), ReadBusTrace(session).execute(0))

    lane = timeline.arrange().lanes[0]
    assert lane.count == 4
    assert lane.marks[-1].seconds == 4.0


def test_the_curves_are_not_doubled_either() -> None:
    session = a_session()
    timeline = ObserveTimeline(session)
    timeline.collect()

    timeline.collect_given(ReadTrace(session).execute(0), ReadBusTrace(session).execute(0))

    assert len(timeline.arrange().curves[0].points) == 3


def test_a_window_filled_only_by_what_is_handed_over_holds_it_all() -> None:
    """The ordinary case: a tab that has been open all along."""
    session = a_session()
    timeline = ObserveTimeline(session)

    timeline.collect_given(ReadTrace(session).execute(0), ReadBusTrace(session).execute(0))

    assert timeline.arrange().lanes[0].count == 3
