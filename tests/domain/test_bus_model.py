"""Invariants of the bus model.

The four kinds of bus are deliberately not averaged into one. An address
carries the kind it belongs to and is checked against it, and what a client
may put on a bus depends on whether the firmware is the master there.
"""

from __future__ import annotations

import pytest

from looper.domain.model.simulation import (
    BusAddress,
    BusDirection,
    BusKind,
    BusMessage,
    BusTraceEntry,
    ComponentDescription,
    SimulatedBus,
)


def test_each_kind_shows_its_address_the_way_that_kind_is_read() -> None:
    assert BusAddress(BusKind.CAN, 0x703).text == "0x703"
    assert BusAddress(BusKind.CAN, 0x703, is_extended=True).text == "0x00000703"
    assert BusAddress(BusKind.I2C, 0x20).text == "0x20"
    assert BusAddress(BusKind.SPI, 1).text == "1"
    assert BusAddress(BusKind.UART, 2).text == "2"


def test_the_same_number_on_two_kinds_is_two_places() -> None:
    """Chip select 2 and I2C address 2 are not the same thing."""
    assert BusAddress(BusKind.SPI, 2) != BusAddress(BusKind.I2C, 2)


def test_an_address_too_wide_for_its_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="wider than a i2c bus addresses"):
        BusAddress(BusKind.I2C, 0x80)
    with pytest.raises(ValueError, match="wider than a can bus addresses"):
        BusAddress(BusKind.CAN, 0x800)

    assert BusAddress(BusKind.CAN, 0x800, is_extended=True).value == 0x800


def test_only_a_can_identifier_can_be_extended() -> None:
    with pytest.raises(ValueError, match="Only a CAN identifier"):
        BusAddress(BusKind.SPI, 1, is_extended=True)


def test_a_negative_address_is_rejected() -> None:
    with pytest.raises(ValueError, match="chip select must not be negative"):
        BusAddress(BusKind.SPI, -1)


def test_only_the_kinds_the_firmware_does_not_master_take_a_message() -> None:
    """On SPI and I2C nothing crosses until the firmware clocks."""
    assert BusMessage(BusAddress(BusKind.CAN, 0x100)).length == 0

    with pytest.raises(ValueError, match="master on a spi bus"):
        BusMessage(BusAddress(BusKind.SPI, 0))
    with pytest.raises(ValueError, match="master on a i2c bus"):
        BusMessage(BusAddress(BusKind.I2C, 0x20))


def test_a_can_message_is_held_to_eight_bytes() -> None:
    with pytest.raises(ValueError, match="at most 8 bytes"):
        BusMessage(BusAddress(BusKind.CAN, 0x100), payload=bytes(9))

    assert BusMessage(BusAddress(BusKind.UART, 0), payload=bytes(9)).length == 9


def test_a_message_shows_its_bytes_as_pairs() -> None:
    message = BusMessage(BusAddress(BusKind.CAN, 0x100), payload=b"\x01\xde")

    assert message.payload_text == "01 DE"


def test_a_message_that_carried_nothing_shows_nothing() -> None:
    """The empty case, because the formatting is not a loop any more."""
    assert BusMessage(BusAddress(BusKind.CAN, 1)).payload_text == ""


def test_every_byte_is_a_pair_of_upper_case_digits() -> None:
    """A busy simulation turns tens of thousands of these into text a second."""
    message = BusMessage(BusAddress(BusKind.UART, 0), payload=bytes(range(16)))

    assert message.payload_text == "00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F"


def test_a_bus_without_a_rate_says_so() -> None:
    assert not SimulatedBus(0, BusKind.SPI, "SPI1").is_configured
    assert SimulatedBus(2, BusKind.CAN, "CAN2", bitrate_bps=500_000).is_configured


def test_a_bus_without_a_label_shows_its_kind_and_number() -> None:
    assert SimulatedBus(1, BusKind.I2C, "").display_name == "i2c 1"


def test_a_negative_rate_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        SimulatedBus(0, BusKind.SPI, "SPI1", bitrate_bps=-1)


def test_a_component_without_a_label_names_its_model_and_place() -> None:
    component = ComponentDescription(
        bus=0, address=BusAddress(BusKind.SPI, 1), label="", model="as8510"
    )

    assert component.display_name == "as8510 at 1"


def test_only_the_two_way_kinds_carry_a_response() -> None:
    assert BusKind.SPI.carries_a_response
    assert BusKind.I2C.carries_a_response
    assert not BusKind.CAN.carries_a_response
    assert not BusKind.UART.carries_a_response


def an_exchange(**changes: object) -> BusTraceEntry:
    """One recorded exchange, with whatever the test wants changed."""
    fields: dict[str, object] = {
        "bus": 0,
        "kind": BusKind.SPI,
        "direction": BusDirection.OUTBOUND,
        "address": BusAddress(BusKind.SPI, 1),
        "payload": b"\x80\xff",
        "response": b"\x00\x41",
        "microseconds": 1_500_000,
        "sequence": 3,
    }
    fields.update(changes)
    return BusTraceEntry(**fields)  # type: ignore[arg-type]


def test_a_recorded_exchange_carries_both_halves_and_its_time() -> None:
    entry = an_exchange()

    assert entry.payload_text == "80 FF"
    assert entry.response_text == "00 41"
    assert entry.seconds == pytest.approx(1.5)
    assert entry.length == 2


def test_an_exchange_that_only_answered_still_reports_a_length() -> None:
    """A read has nothing in the outgoing half, and its length is what came back."""
    entry = an_exchange(payload=b"", response=b"\x01\x02\x03")

    assert entry.length == 3


def test_an_exchange_nothing_took_is_marked_rather_than_dropped() -> None:
    assert an_exchange(accepted=False).was_refused
    assert not an_exchange().was_refused


def test_direction_is_named_from_the_firmware() -> None:
    assert BusDirection.OUTBOUND.is_from_firmware
    assert not BusDirection.INBOUND.is_from_firmware
