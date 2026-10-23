"""Invariants of the analog model and its signals."""

from __future__ import annotations

import pytest

from looper.domain.model.simulation import (
    AnalogChannel,
    AnalogSample,
    ChannelDirection,
    SignalDefinition,
    Waveform,
)


def test_a_constant_signal_holds_its_offset() -> None:
    signal = SignalDefinition(waveform=Waveform.CONSTANT, offset=2.5, amplitude=9.0)

    assert signal.is_static
    assert signal.minimum == signal.maximum == 2.5
    assert signal.period_seconds is None


def test_an_alternating_signal_swings_around_its_offset() -> None:
    signal = SignalDefinition(waveform=Waveform.SINE, amplitude=5.0, offset=1.0, frequency_hz=50.0)

    assert not signal.is_static
    assert (signal.minimum, signal.maximum) == (-4.0, 6.0)
    assert signal.period_seconds == pytest.approx(0.02)


def test_a_waveform_without_a_frequency_cannot_move() -> None:
    signal = SignalDefinition(waveform=Waveform.SQUARE, amplitude=1.0, frequency_hz=0.0)

    assert signal.is_static


def test_negative_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="frequency must not be negative"):
        SignalDefinition(frequency_hz=-1.0)
    with pytest.raises(ValueError, match="amplitude must not be negative"):
        SignalDefinition(amplitude=-1.0)


def test_only_an_input_channel_may_be_driven() -> None:
    reading = AnalogChannel(1, "SHUNT", "A", ChannelDirection.INPUT, 0.0)
    writing = AnalogChannel(2, "POWER", "W", ChannelDirection.OUTPUT, 0.0)

    assert reading.is_drivable_by_client
    assert not writing.is_drivable_by_client


def test_an_unlabelled_channel_falls_back_to_its_number() -> None:
    assert AnalogChannel(7, "", "A", ChannelDirection.INPUT, 0.0).display_name == "channel 7"


def test_dc_is_the_readable_name_of_a_constant() -> None:
    assert Waveform.CONSTANT.display_name == "DC"
    assert Waveform.SINE.display_name == "Sine"
    assert not Waveform.CONSTANT.is_alternating


def test_a_sample_reports_its_time_in_seconds() -> None:
    assert AnalogSample(1, 1_500_000, 2.0, 9).seconds == pytest.approx(1.5)
