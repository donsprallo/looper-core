"""What crossed a bus, arranged by who was talking.

A table answers "what happened" and makes the reader assemble "who
said what to whom" out of two columns, row by row. The arranging is
what is tested here, and the two things it adds that a row cannot
carry: the gap since the last turn, which a ladder's even spacing
destroys, and which party never took anything at all.
"""

from __future__ import annotations

import pytest

from looper.domain.model.simulation import (
    BusAddress,
    BusDirection,
    BusKind,
    BusTraceEntry,
)
from looper.domain.services import Conversation, Turn, conversation_of

SECOND = 1_000_000
CONVERTER = BusAddress(BusKind.SPI, 0)
EXPANDER = BusAddress(BusKind.SPI, 1)


def an_exchange(
    seconds: float,
    address: BusAddress = CONVERTER,
    response: bytes = b"",
    accepted: bool = True,
    inbound: bool = False,
) -> BusTraceEntry:
    """One exchange on the SPI bus."""
    return BusTraceEntry(
        bus=0,
        kind=BusKind.SPI,
        direction=BusDirection.INBOUND if inbound else BusDirection.OUTBOUND,
        address=address,
        payload=b"\x80\xff",
        response=response,
        accepted=accepted,
        microseconds=int(seconds * SECOND),
    )


def test_a_party_gets_a_column_the_first_time_it_is_addressed() -> None:
    """In that order, so the columns stay put as more is recorded."""
    spoken = conversation_of(
        [an_exchange(1.0, EXPANDER), an_exchange(1.1, CONVERTER), an_exchange(1.2, EXPANDER)]
    )

    assert spoken.addresses == (EXPANDER, CONVERTER)
    assert spoken.column_of(EXPANDER) == 0
    assert spoken.column_of(CONVERTER) == 1


def test_each_turn_carries_the_gap_since_the_last_one() -> None:
    """A ladder spaces its rows evenly, so the time has to be written."""
    spoken = conversation_of([an_exchange(1.0), an_exchange(1.25), an_exchange(1.3)])

    assert [one.gap_seconds for one in spoken.turns] == pytest.approx([0.0, 0.25, 0.05])


def test_the_first_turn_has_nothing_to_measure_from() -> None:
    spoken = conversation_of([an_exchange(5.0)])

    assert spoken.turns[0].gap_seconds == 0.0


def test_a_turn_knows_who_started_it() -> None:
    spoken = conversation_of([an_exchange(1.0), an_exchange(1.1, inbound=True)])

    assert [one.is_outbound for one in spoken.turns] == [True, False]


def test_an_answer_inside_the_exchange_is_told_from_none() -> None:
    """SPI and I2C answer at once; on CAN an answer is a later turn."""
    spoken = conversation_of([an_exchange(1.0, response=b"\x01"), an_exchange(1.1)])

    assert [one.was_answered for one in spoken.turns] == [True, False]


def test_a_party_that_never_took_anything_is_named() -> None:
    """The single most useful thing a bus view can point at."""
    spoken = conversation_of(
        [
            an_exchange(1.0, CONVERTER, response=b"\x01"),
            an_exchange(1.1, EXPANDER, accepted=False),
            an_exchange(1.2, EXPANDER, accepted=False),
        ]
    )

    assert spoken.silent_addresses == (EXPANDER,)


def test_a_party_that_took_something_once_is_not_called_silent() -> None:
    spoken = conversation_of(
        [an_exchange(1.0, EXPANDER, accepted=False), an_exchange(1.1, EXPANDER)]
    )

    assert spoken.silent_addresses == ()


def test_a_bus_nothing_crossed_is_an_empty_conversation() -> None:
    spoken = conversation_of([])

    assert spoken.is_empty
    assert spoken.addresses == ()
    assert spoken.silent_addresses == ()


def test_a_conversation_does_not_run_backwards() -> None:
    with pytest.raises(ValueError, match="does not run backwards"):
        Turn(exchange=an_exchange(1.0), gap_seconds=-0.1)


def test_an_empty_conversation_is_the_default() -> None:
    assert Conversation().is_empty
