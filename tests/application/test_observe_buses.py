"""What a client is told about the buses and what is attached to them.

The use cases here turn an exchange into something a table can show. The
one thing the listing must never do quietly is drop an exchange nothing
took -- that is the answer to "I sent it and nothing happened".
"""

from __future__ import annotations

import pytest
from simulation_doubles import RecordingSession

from looper.application.commands import SendBusMessage
from looper.application.queries import ObserveBuses, ObserveComponents, ReadBusTrace
from looper.domain.model.simulation import (
    BusAddress,
    BusDirection,
    BusKind,
    BusMessage,
    BusTraceEntry,
    ComponentDescription,
    SimulatedBus,
)


def an_exchange(sequence: int, accepted: bool = True) -> BusTraceEntry:
    """One recorded SPI transfer."""
    return BusTraceEntry(
        bus=0,
        kind=BusKind.SPI,
        direction=BusDirection.OUTBOUND,
        address=BusAddress(BusKind.SPI, 1),
        payload=b"\x80\xff",
        response=b"\x00\x41",
        accepted=accepted,
        microseconds=2_500_000,
        sequence=sequence,
    )


def test_a_bus_reports_its_kind_and_the_rate_the_firmware_set() -> None:
    session = RecordingSession()
    session.buses = (
        SimulatedBus(0, BusKind.SPI, "SPI1"),
        SimulatedBus(2, BusKind.CAN, "CAN2", bitrate_bps=500_000),
    )

    buses = ObserveBuses(session).execute()

    assert [(bus.name, bus.kind) for bus in buses] == [("SPI1", "spi"), ("CAN2", "can")]
    assert buses[0].display_bitrate == "not configured"
    assert buses[1].display_bitrate == "500 kbit/s"


def test_only_the_kinds_the_firmware_does_not_master_offer_a_form() -> None:
    session = RecordingSession()
    session.buses = (
        SimulatedBus(0, BusKind.SPI, "SPI1"),
        SimulatedBus(1, BusKind.I2C, "I2C1"),
        SimulatedBus(2, BusKind.CAN, "CAN2"),
        SimulatedBus(3, BusKind.UART, "UART1"),
    )

    offered = {bus.kind: bus.accepts_messages for bus in ObserveBuses(session).execute()}

    assert offered == {"spi": False, "i2c": False, "can": True, "uart": True}


def test_a_component_is_listed_where_it_sits() -> None:
    session = RecordingSession()
    session.components = (
        ComponentDescription(
            bus=1, address=BusAddress(BusKind.I2C, 0x20), label="IO expander", model="mcp23x08"
        ),
    )

    listed = ObserveComponents(session).execute()[0]

    assert (listed.bus_id, listed.address, listed.model) == (1, "0x20", "mcp23x08")
    assert listed.name == "IO expander"


def test_an_exchange_is_shown_with_both_halves() -> None:
    session = RecordingSession()
    session.exchanges = (an_exchange(sequence=0),)

    row = ReadBusTrace(session).execute().exchanges[0]

    assert (row.kind, row.address, row.payload, row.response) == ("spi", "1", "80 FF", "00 41")
    assert row.seconds == pytest.approx(2.5)
    assert row.length == 2


def test_an_exchange_nothing_took_is_marked_rather_than_dropped() -> None:
    session = RecordingSession()
    session.exchanges = (an_exchange(sequence=0, accepted=False),)

    assert ReadBusTrace(session).execute().exchanges[0].was_refused


def test_reading_continues_from_the_sequence_number_already_seen() -> None:
    session = RecordingSession()
    session.exchanges = tuple(an_exchange(sequence=number) for number in range(3))

    view = ReadBusTrace(session).execute(after_sequence=2)

    assert [row.sequence for row in view.exchanges] == [2]


def test_clearing_reaches_the_simulation() -> None:
    session = RecordingSession()

    ReadBusTrace(session).clear()

    assert session.cleared == ["bus trace"]


def test_a_message_described_by_its_parts_reaches_the_simulation() -> None:
    session = RecordingSession()

    SendBusMessage(session).send_payload(2, BusKind.CAN, 0x6FF, b"\x01\x02")

    bus, message = session.sent[0]
    assert bus == 2
    assert message == BusMessage(BusAddress(BusKind.CAN, 0x6FF), b"\x01\x02")


def test_an_extended_identifier_is_sent_as_one() -> None:
    session = RecordingSession()

    SendBusMessage(session).send_payload(2, BusKind.CAN, 0x1234, b"", extended=True)

    assert session.sent[0][1].address.is_extended


def test_a_bus_the_firmware_masters_is_refused_before_anything_is_sent() -> None:
    session = RecordingSession()

    with pytest.raises(ValueError, match="master on a spi bus"):
        SendBusMessage(session).send_payload(0, BusKind.SPI, 1, b"\x01")

    assert session.sent == []


def test_an_address_too_wide_is_refused_before_anything_is_sent() -> None:
    session = RecordingSession()

    with pytest.raises(ValueError, match="wider than a can bus"):
        SendBusMessage(session).send_payload(2, BusKind.CAN, 0x1234, b"")

    assert session.sent == []
