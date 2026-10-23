"""Invariants of the observable simulation state."""

from __future__ import annotations

import pytest

from looper.domain.model.simulation import (
    ActivePolarity,
    GpioPinState,
    PinDirection,
    PinIdentifier,
    SignalLevel,
    SimulationTime,
    TimeMode,
)


def test_a_pin_identity_ignores_its_display_label() -> None:
    bare = PinIdentifier(value=0x0A03)

    assert bare == bare.labelled("LED_STATUS")
    assert hash(bare) == hash(bare.labelled("LED_STATUS"))


def test_an_unlabelled_pin_displays_its_hexadecimal_value() -> None:
    assert PinIdentifier(value=0x0A03).display_name == "0x00000A03"


def test_an_active_low_pin_is_active_while_driven_low() -> None:
    pin = GpioPinState(
        identifier=PinIdentifier(value=1),
        direction=PinDirection.OUTPUT,
        level=SignalLevel.LOW,
        polarity=ActivePolarity.ACTIVE_LOW,
    )

    assert pin.is_active
    assert not pin.toggled().is_active
    assert not pin.is_drivable_by_client


def test_negative_simulation_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        SimulationTime(microseconds=-1)


def test_elapsed_milliseconds_truncate_towards_zero() -> None:
    assert SimulationTime(microseconds=1_999).milliseconds == 1
    assert SimulationTime(microseconds=0).advanced_by(2_500).milliseconds == 2


def test_only_real_time_supports_interactive_inspection() -> None:
    assert TimeMode.REAL_TIME.supports_interactive_inspection
    assert not TimeMode.VIRTUAL.supports_interactive_inspection
