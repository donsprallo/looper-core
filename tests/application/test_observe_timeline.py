"""Three recordings assembled onto one stretch of time.

The arranging is what is worth testing: that a measured value, an
exchange and a call recorded at the same instant end up at the same
place on the ruler, that a window keeps the last few seconds and
drops the rest, and that a row with nothing in view is still a row.
"""

from __future__ import annotations

from simulation_doubles import RecordingSession

from looper.application.queries import ObserveTimeline
from looper.domain.model.simulation import (
    AdapterCall,
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
SPI = SimulatedBus(identifier=1, kind=BusKind.SPI, label="SPI1")
POWER = AnalogChannel(
    identifier=2,
    label="POWER",
    unit="W",
    direction=ChannelDirection.OUTPUT,
    value=400.0,
)


def a_sample(seconds: float, sequence: int, value: float = 1.0) -> AnalogSample:
    """One recorded value of the power channel."""
    return AnalogSample(
        channel=POWER.identifier,
        microseconds=int(seconds * SECOND),
        value=value,
        sequence=sequence,
    )


def an_exchange(seconds: float, sequence: int, accepted: bool = True) -> BusTraceEntry:
    """One CAN frame that crossed."""
    return BusTraceEntry(
        bus=CAN.identifier,
        kind=BusKind.CAN,
        direction=BusDirection.OUTBOUND,
        address=BusAddress(BusKind.CAN, 0x702),
        payload=b"\x01\x02",
        accepted=accepted,
        microseconds=int(seconds * SECOND),
        sequence=sequence,
    )


def a_call(seconds: float, sequence: int, function: str = "adapter_can_send") -> AdapterCall:
    """One adapter call the journal recorded."""
    return AdapterCall(function=function, microseconds=int(seconds * SECOND), sequence=sequence)


def a_session(**recorded: object) -> RecordingSession:
    """A simulation that recorded what the test says it recorded."""
    session = RecordingSession()
    session.channels = (POWER,)
    session.buses = (CAN, SPI)
    for name, value in recorded.items():
        setattr(session, name, value)
    return session


def test_every_bus_is_a_row_whether_it_carried_anything_or_not() -> None:
    """A bus with no traffic is a finding; a missing row is a puzzle."""
    view = ObserveTimeline(a_session(exchanges=(an_exchange(1.0, 0),))).execute()

    assert [lane.label for lane in view.lanes if lane.kind == "bus"] == ["CAN1", "SPI1"]
    assert view.lanes[1].is_empty


def test_an_exchange_lands_on_its_own_bus() -> None:
    view = ObserveTimeline(a_session(exchanges=(an_exchange(1.0, 0),))).execute()

    marks = view.lanes[0].marks
    assert len(marks) == 1
    assert marks[0].seconds == 1.0
    assert marks[0].label == "0x702"


def test_what_an_exchange_carried_is_written_beside_it() -> None:
    view = ObserveTimeline(a_session(exchanges=(an_exchange(1.0, 0),))).execute()

    assert "0102" in view.lanes[0].marks[0].detail.replace(" ", "")


def test_an_exchange_nothing_took_is_marked_as_doubtful() -> None:
    """Those are what a reader is hunting through a hundred frames for."""
    session = a_session(exchanges=(an_exchange(1.0, 0, accepted=False),))

    view = ObserveTimeline(session).execute()

    assert view.lanes[0].marks[0].is_doubtful


def test_calls_are_gathered_into_a_row_for_each_peripheral() -> None:
    session = a_session(
        calls=(
            a_call(1.0, 0, "adapter_can_send"),
            a_call(1.1, 1, "adapter_spi_transfer"),
            a_call(1.2, 2, "adapter_can_receive"),
        )
    )

    view = ObserveTimeline(session).execute()

    rows = {lane.label: len(lane.marks) for lane in view.lanes if lane.kind == "call"}
    assert rows == {"can calls": 2, "spi calls": 1}


def test_a_measured_value_becomes_a_curve_with_its_unit() -> None:
    session = a_session(samples=(a_sample(1.0, 0, 400.0), a_sample(1.1, 1, 410.0)))

    view = ObserveTimeline(session).execute()

    assert [curve.label for curve in view.curves] == ["POWER [W]"]
    assert view.curves[0].points == ((1.0, 400.0), (1.1, 410.0))
    assert view.curves[0].highest == 410.0


def test_everything_recorded_at_one_instant_lands_at_one_place() -> None:
    """The whole reason for the page: one clock, one ruler."""
    session = a_session(
        samples=(a_sample(2.5, 0),),
        exchanges=(an_exchange(2.5, 0),),
        calls=(a_call(2.5, 0),),
    )

    view = ObserveTimeline(session).execute()

    assert view.curves[0].points[0][0] == 2.5
    assert view.lanes[0].marks[0].seconds == 2.5
    assert [one.marks[0].seconds for one in view.lanes if one.kind == "call"] == [2.5]


def test_the_window_ends_at_the_newest_thing_recorded() -> None:
    session = a_session(exchanges=(an_exchange(9.0, 0),))

    view = ObserveTimeline(session, window_seconds=2.0).execute()

    assert view.window.end_seconds == 9.0
    assert view.window.start_seconds == 7.0


def test_what_fell_out_of_the_window_is_dropped() -> None:
    """A page nobody closed should not grow without end."""
    session = a_session(
        samples=(a_sample(1.0, 0), a_sample(9.0, 1)),
        exchanges=(an_exchange(1.0, 0), an_exchange(9.0, 1)),
    )

    view = ObserveTimeline(session, window_seconds=2.0).execute()

    assert view.curves[0].points == ((9.0, 1.0),)
    assert [mark.seconds for mark in view.lanes[0].marks] == [9.0]


def test_a_row_says_how_regular_it_was() -> None:
    session = a_session(
        exchanges=tuple(an_exchange(index * 0.1, index) for index in range(5)),
    )

    view = ObserveTimeline(session).execute()

    assert "every 100.0 ms" in view.lanes[0].summary


def test_a_row_with_one_thing_on_it_claims_no_period() -> None:
    session = a_session(exchanges=(an_exchange(1.0, 0),))

    view = ObserveTimeline(session).execute()

    assert view.lanes[0].summary == ""


def test_a_call_already_seen_is_not_counted_twice() -> None:
    """The journal hands over its most recent page on every reading."""
    session = a_session(calls=(a_call(1.0, 0), a_call(1.1, 1)))
    timeline = ObserveTimeline(session)

    timeline.execute()
    view = timeline.execute()

    assert [len(lane.marks) for lane in view.lanes if lane.kind == "call"] == [2]


def test_clearing_starts_the_window_again() -> None:
    session = a_session(exchanges=(an_exchange(1.0, 0),))
    timeline = ObserveTimeline(session)
    timeline.execute()

    timeline.clear()
    session.exchanges = ()
    view = timeline.execute()

    assert view.is_empty
    assert view.recorded is None


def test_a_call_row_that_lost_some_says_so_instead_of_measuring() -> None:
    """A period measured across a hole is a reading of the hole."""
    session = a_session(calls=(a_call(1.0, 0), a_call(1.1, 1)))
    timeline = ObserveTimeline(session)
    timeline.execute()

    session.calls = (a_call(2.0, 40), a_call(2.1, 41))
    view = timeline.execute()

    rows = [lane for lane in view.lanes if lane.kind == "call"]
    assert rows[0].summary == "sampled, gaps not shown"


def test_what_the_journal_forgot_before_anybody_looked_is_not_a_gap() -> None:
    """A ring that wrapped before the page opened owes the page nothing."""
    session = a_session(calls=(a_call(1.0, 500), a_call(1.1, 501), a_call(1.2, 502)))

    view = ObserveTimeline(session).execute()

    rows = [lane for lane in view.lanes if lane.kind == "call"]
    assert "every" in rows[0].summary


def test_a_bus_row_is_never_called_sampled() -> None:
    """The bus trace is read by sequence until it is caught up."""
    session = a_session(
        exchanges=tuple(an_exchange(index * 0.1, index) for index in range(5)),
        calls=(a_call(1.0, 0),),
    )
    timeline = ObserveTimeline(session)
    timeline.execute()
    session.calls = (a_call(2.0, 40),)

    view = timeline.execute()

    assert "sampled" not in view.lanes[0].summary
