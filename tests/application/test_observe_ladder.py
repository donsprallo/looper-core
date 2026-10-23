"""One bus read as a conversation, on its way to the drawing.

The domain decides who was talking and when; what is tested here is
what the columns end up called, what a reader is told about the bus
as a whole, and that choosing another bus does not leave the last
one's traffic behind.
"""

from __future__ import annotations

from simulation_doubles import RecordingSession

from looper.application.queries import ObserveLadder
from looper.domain.model.simulation import (
    BusAddress,
    BusDirection,
    BusKind,
    BusTraceEntry,
    ComponentDescription,
    SimulatedBus,
)

SECOND = 1_000_000
SPI = SimulatedBus(identifier=0, kind=BusKind.SPI, label="SPI1")
CAN = SimulatedBus(identifier=1, kind=BusKind.CAN, label="CAN1")
CONVERTER = BusAddress(BusKind.SPI, 0)
EMPTY_SEAT = BusAddress(BusKind.SPI, 1)
AS8510 = ComponentDescription(bus=0, address=CONVERTER, label="AS8510", model="as8510")


def an_exchange(
    seconds: float,
    sequence: int,
    bus: int = 0,
    address: BusAddress = CONVERTER,
    response: bytes = b"",
    accepted: bool = True,
) -> BusTraceEntry:
    """One exchange on a bus."""
    return BusTraceEntry(
        bus=bus,
        kind=address.kind,
        direction=BusDirection.OUTBOUND,
        address=address,
        payload=b"\x80\xff",
        response=response,
        accepted=accepted,
        microseconds=int(seconds * SECOND),
        sequence=sequence,
    )


def a_session(*exchanges: BusTraceEntry) -> RecordingSession:
    """A simulation with two buses and one component."""
    session = RecordingSession()
    session.buses = (SPI, CAN)
    session.components = (AS8510,)
    session.exchanges = exchanges
    return session


def test_nothing_is_read_until_a_bus_is_chosen() -> None:
    """A ladder is read closely, and four at once is none of them."""
    ladder = ObserveLadder(a_session(an_exchange(1.0, 0)))

    assert ladder.execute().is_empty
    assert ladder.bus is None


def test_a_column_is_named_after_the_component_that_answers_there() -> None:
    ladder = ObserveLadder(a_session(an_exchange(1.0, 0, response=b"\x01")))
    ladder.listen_to(SPI.identifier)

    view = ladder.execute()

    assert [one.name for one in view.parties] == ["AS8510"]
    assert view.bus_name == "SPI1"


def test_a_column_nothing_answers_at_is_named_after_the_place() -> None:
    """A heading of `1` could be a chip select, a port or a device."""
    ladder = ObserveLadder(a_session(an_exchange(1.0, 0, address=EMPTY_SEAT, accepted=False)))
    ladder.listen_to(SPI.identifier)

    view = ladder.execute()

    assert [one.name for one in view.parties] == ["chip select 1"]
    assert view.parties[0].is_silent


def test_the_bus_is_told_which_parties_never_answered() -> None:
    ladder = ObserveLadder(
        a_session(
            an_exchange(1.0, 0, response=b"\x01"),
            an_exchange(1.1, 1, address=EMPTY_SEAT, accepted=False),
        )
    )
    ladder.listen_to(SPI.identifier)

    assert "chip select 1" in ladder.execute().note


def test_a_bus_where_everything_was_taken_says_so() -> None:
    """Taken rather than answered: on CAN a filter takes and nobody replies."""
    ladder = ObserveLadder(a_session(an_exchange(1.0, 0, response=b"\x01")))
    ladder.listen_to(SPI.identifier)

    assert "Everything that was addressed was taken" in ladder.execute().note


def test_what_crossed_another_bus_is_left_out() -> None:
    ladder = ObserveLadder(a_session(an_exchange(1.0, 0), an_exchange(1.1, 1, bus=1)))
    ladder.listen_to(SPI.identifier)

    assert len(ladder.execute().steps) == 1


def test_choosing_another_bus_forgets_the_last_one() -> None:
    """Otherwise its traffic would appear in a conversation it had no part in."""
    session = a_session(an_exchange(1.0, 0))
    ladder = ObserveLadder(session)
    ladder.listen_to(SPI.identifier)
    ladder.execute()

    ladder.listen_to(CAN.identifier)

    assert ladder.execute().is_empty


def test_the_gap_since_the_last_turn_is_written_out() -> None:
    """A ladder spaces its rows evenly, so the clock has to be in words."""
    ladder = ObserveLadder(a_session(an_exchange(1.0, 0), an_exchange(1.0002, 1)))
    ladder.listen_to(SPI.identifier)

    assert [one.gap for one in ladder.execute().steps] == ["", "+200 us"]


def test_what_was_carried_reaches_the_drawing_as_hexadecimal() -> None:
    ladder = ObserveLadder(a_session(an_exchange(1.0, 0, response=b"\x0a\x73")))
    ladder.listen_to(SPI.identifier)

    step = ladder.execute().steps[0]
    assert step.payload == "80 FF"
    assert step.response == "0A 73"
    assert step.was_answered
