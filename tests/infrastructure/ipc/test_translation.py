"""Translation between protocol messages and the domain model."""

from __future__ import annotations

from looper.domain.model.simulation import (
    ActivePolarity,
    PinDirection,
    SignalLevel,
    TimeMode,
)
from looper.infrastructure.ipc import translation
from looper.infrastructure.ipc.generated import looper_control_pb2 as protocol


def test_a_labelled_pin_keeps_its_name() -> None:
    message = protocol.Pin(
        id=17,
        label="LED_STATUS",
        direction=protocol.PIN_DIRECTION_OUTPUT,
        level=protocol.SIGNAL_LEVEL_HIGH,
        polarity=protocol.ACTIVE_POLARITY_HIGH,
    )

    pin = translation.to_pin_state(message)

    assert pin.identifier.display_name == "LED_STATUS"
    assert pin.direction is PinDirection.OUTPUT
    assert pin.level is SignalLevel.HIGH
    assert pin.is_active


def test_an_unlabelled_pin_falls_back_to_its_number() -> None:
    pin = translation.to_pin_state(protocol.Pin(id=0x2A))

    assert pin.identifier.display_name == "0x0000002A"


def test_an_unset_direction_is_read_as_an_output() -> None:
    pin = translation.to_pin_state(protocol.Pin(id=1))

    assert pin.direction is PinDirection.OUTPUT
    assert not pin.is_drivable_by_client


def test_an_active_low_pin_is_active_while_low() -> None:
    message = protocol.Pin(
        id=4,
        direction=protocol.PIN_DIRECTION_INPUT,
        level=protocol.SIGNAL_LEVEL_LOW,
        polarity=protocol.ACTIVE_POLARITY_LOW,
    )

    pin = translation.to_pin_state(message)

    assert pin.polarity is ActivePolarity.ACTIVE_LOW
    assert pin.is_active
    assert pin.is_drivable_by_client


def test_time_modes_map_both_ways() -> None:
    assert translation.to_time_mode(protocol.TIME_MODE_REAL) is TimeMode.REAL_TIME
    assert translation.to_time_mode(protocol.TIME_MODE_VIRTUAL) is TimeMode.VIRTUAL
    assert translation.to_time_mode(protocol.TIME_MODE_UNSPECIFIED) is TimeMode.VIRTUAL


def test_levels_map_to_the_protocol() -> None:
    assert translation.from_signal_level(SignalLevel.HIGH) == protocol.SIGNAL_LEVEL_HIGH
    assert translation.from_signal_level(SignalLevel.LOW) == protocol.SIGNAL_LEVEL_LOW
