"""The whole chain, from a header to a running simulation a client drives.

This test parses an adapter header, generates its simulation, compiles it
together with the runtime and the example firmware, starts the result as a
separate process, and talks to it over the control protocol.

It is also the cross check of the two protobuf implementations: the C encoder
in the runtime and the reference implementation on the Python side never see
each other's source, only the wire.

Building and starting the simulation lives in conftest.py, which both
integration modules share.
"""

from __future__ import annotations

import time

import pytest

from looper.application.commands import DrivePin
from looper.application.queries import ObserveSimulation
from looper.domain.model.simulation import SignalLevel, TimeMode
from looper.domain.ports import SimulationRejectedError
from looper.infrastructure.ipc import ProtobufSimulationSession

LED_NAME = "LED_STATUS"
BUTTON_NAME = "BUTTON_MODE"


def test_the_simulation_reports_its_registered_pins(
    real_time_session: ProtobufSimulationSession,
) -> None:
    view = ObserveSimulation(real_time_session).execute()

    names = {pin.name for pin in view.pins}
    assert names == {LED_NAME, BUTTON_NAME}
    assert view.time_mode == TimeMode.REAL_TIME.value


def test_an_output_is_not_drivable_and_an_input_is(
    real_time_session: ProtobufSimulationSession,
) -> None:
    view = ObserveSimulation(real_time_session).execute()
    pins = {pin.name: pin for pin in view.pins}

    assert not pins[LED_NAME].is_drivable
    assert pins[BUTTON_NAME].is_drivable


def test_driving_an_input_reaches_the_firmware(
    real_time_session: ProtobufSimulationSession,
) -> None:
    button = next(
        pin
        for pin in ObserveSimulation(real_time_session).execute().pins
        if pin.name == BUTTON_NAME
    )
    assert not button.is_active

    DrivePin(real_time_session).execute(button.pin_id, SignalLevel.LOW)

    after = next(
        pin
        for pin in ObserveSimulation(real_time_session).execute().pins
        if pin.name == BUTTON_NAME
    )
    assert after.level == SignalLevel.LOW.value
    assert after.is_active


def test_driving_an_output_is_refused(real_time_session: ProtobufSimulationSession) -> None:
    led = next(
        pin for pin in ObserveSimulation(real_time_session).execute().pins if pin.name == LED_NAME
    )

    with pytest.raises(SimulationRejectedError, match="output"):
        DrivePin(real_time_session).execute(led.pin_id, SignalLevel.HIGH)


def test_the_journal_records_the_adapter_calls_the_firmware_made(
    real_time_session: ProtobufSimulationSession,
) -> None:
    real_time_session.clear_journal()
    time.sleep(0.1)

    recorded = {entry.function for entry in real_time_session.read_journal()}

    assert "adapter_blinky_millis" in recorded
    assert "adapter_blinky_gpio_get" in recorded


def test_real_time_advances_on_its_own(real_time_session: ProtobufSimulationSession) -> None:
    first = real_time_session.read_time()
    time.sleep(0.05)
    second = real_time_session.read_time()

    assert second > first


def test_real_time_cannot_be_advanced_by_a_client(
    real_time_session: ProtobufSimulationSession,
) -> None:
    with pytest.raises(SimulationRejectedError, match="real time"):
        real_time_session.advance_time(1000)


def test_a_client_can_advance_the_virtual_clock(
    virtual_time_session: ProtobufSimulationSession,
) -> None:
    """A client jump is applied on top of whatever the firmware did.

    The example advances its own virtual clock once per idle loop, so this
    does not assert that the clock stands still without a client.
    """
    assert virtual_time_session.time_mode is TimeMode.VIRTUAL

    before = virtual_time_session.read_time()
    reached = virtual_time_session.advance_time(500_000)

    assert reached.microseconds >= before.microseconds + 500_000
