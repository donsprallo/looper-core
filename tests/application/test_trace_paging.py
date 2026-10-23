"""Reading a trace that arrives faster than a client asks for it.

One reply carries a few hundred samples; a firmware produces thousands
a second. A reader that took one reply per poll would show a burst of
signal and then a gap, and the gap would move -- which is exactly what
a signal above a few hertz looks like when it cannot be plotted.
"""

from __future__ import annotations

from simulation_doubles import RecordingSession

from looper.application.queries import ReadBusTrace, ReadTrace
from looper.domain.model.simulation import (
    AnalogSample,
    BusAddress,
    BusDirection,
    BusKind,
    BusTraceEntry,
)

PER_REPLY = 512

#: What the simulation sends in one reply of bus exchanges.
EXCHANGES_PER_REPLY = 64


class PagingSession(RecordingSession):
    """A session that answers a few hundred samples at a time.

    Which is what the real one does, and what the reading has to cope
    with. The sequence it reports as next is where the recording has
    got to, not where the reader has -- the trap this exists to catch.
    """

    def __init__(self, produced: int) -> None:
        super().__init__()
        self.samples = tuple(
            AnalogSample(channel=0, microseconds=index * 100, value=float(index), sequence=index)
            for index in range(produced)
        )
        self.replies = 0

    def read_trace(self, after_sequence: int = 0) -> tuple[tuple[AnalogSample, ...], int]:
        self.replies += 1
        waiting = tuple(one for one in self.samples if one.sequence >= after_sequence)
        return waiting[:PER_REPLY], len(self.samples)


def test_a_reading_keeps_asking_until_it_has_everything() -> None:
    session = PagingSession(produced=1600)

    view = ReadTrace(session).execute(0)

    assert len(view.samples) == 1600
    assert session.replies == 4


def test_one_reply_is_enough_when_one_reply_holds_it_all() -> None:
    session = PagingSession(produced=100)

    view = ReadTrace(session).execute(0)

    assert len(view.samples) == 100
    assert session.replies == 1


def test_nothing_recorded_asks_once_and_stops() -> None:
    session = PagingSession(produced=0)

    view = ReadTrace(session).execute(0)

    assert view.samples == ()
    assert session.replies == 1


def test_a_reading_continues_from_where_the_last_one_stopped() -> None:
    session = PagingSession(produced=1600)

    view = ReadTrace(session).execute(1500)

    assert [one.sequence for one in view.samples][:1] == [1500]
    assert len(view.samples) == 100


def test_the_reading_reports_where_the_recording_has_got_to() -> None:
    """A caller pages with this, so it has to be the end rather than a page."""
    session = PagingSession(produced=1600)

    view = ReadTrace(session).execute(0)

    assert view.next_sequence == 1600


def test_a_reader_that_never_catches_up_still_returns() -> None:
    """A firmware can always outrun a client; it must not hang the poll."""
    session = PagingSession(produced=PER_REPLY * 500)

    view = ReadTrace(session).execute(0)

    assert view.samples
    assert session.replies <= 100


class PagingBusSession(RecordingSession):
    """A session that answers a page of exchanges at a time.

    The same trap on the other recording: it reports where the
    recording has got to, not where the reader has. A bus table that
    paged by that number would simply be missing every burst.
    """

    def __init__(self, crossed: int) -> None:
        super().__init__()
        self.exchanges = tuple(
            BusTraceEntry(
                bus=0,
                kind=BusKind.CAN,
                direction=BusDirection.OUTBOUND,
                address=BusAddress(BusKind.CAN, 0x700 + index % 8),
                microseconds=index * 1000,
                sequence=index,
            )
            for index in range(crossed)
        )
        self.replies = 0

    def read_bus_trace(self, after_sequence: int = 0) -> tuple[tuple[BusTraceEntry, ...], int]:
        self.replies += 1
        waiting = tuple(one for one in self.exchanges if one.sequence >= after_sequence)
        return waiting[:EXCHANGES_PER_REPLY], len(self.exchanges)


def test_a_bus_reading_keeps_asking_until_it_has_everything() -> None:
    """Otherwise a burst of frames is missing from the list entirely."""
    session = PagingBusSession(crossed=200)

    view = ReadBusTrace(session).execute(0)

    assert len(view.exchanges) == 200
    assert session.replies == 4


def test_a_bus_reading_continues_from_where_the_last_one_stopped() -> None:
    session = PagingBusSession(crossed=200)

    view = ReadBusTrace(session).execute(190)

    assert [one.sequence for one in view.exchanges] == list(range(190, 200))


def test_a_quiet_bus_is_asked_once() -> None:
    session = PagingBusSession(crossed=0)

    view = ReadBusTrace(session).execute(0)

    assert view.exchanges == ()
    assert session.replies == 1


def test_the_bus_reading_reports_where_the_recording_has_got_to() -> None:
    session = PagingBusSession(crossed=200)

    assert ReadBusTrace(session).execute(0).next_sequence == 200
