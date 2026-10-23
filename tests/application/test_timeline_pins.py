"""Pins on the ruler, as the stretches they spent at a level.

A logic analyser draws bands, not moments, and the two ends of a band
are where it can lie. The last stretch has no change to close it and
must reach the edge of the window, or a pin that is still high looks
like one that stopped. The time before the first recorded level is
not time the pin spent low; it is time nobody watched it.
"""

from __future__ import annotations

from simulation_doubles import RecordingSession

from looper.application.queries import ObserveTimeline
from looper.domain.model.simulation import (
    ActivePolarity,
    AnalogChannel,
    BusAddress,
    BusDirection,
    BusKind,
    BusTraceEntry,
    ChannelDirection,
    GpioPinState,
    PinChange,
    PinDirection,
    PinIdentifier,
    SignalLevel,
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


def an_exchange(seconds: float, sequence: int) -> BusTraceEntry:
    """One CAN frame that crossed."""
    return BusTraceEntry(
        bus=CAN.identifier,
        kind=BusKind.CAN,
        direction=BusDirection.OUTBOUND,
        address=BusAddress(BusKind.CAN, 0x702),
        microseconds=int(seconds * SECOND),
        sequence=sequence,
    )


def a_session(**recorded: object) -> RecordingSession:
    """A simulation that recorded what the test says it recorded."""
    session = RecordingSession()
    session.channels = (POWER,)
    session.buses = (CAN, SPI)
    session.pins = (SELECT,)
    for name, value in recorded.items():
        setattr(session, name, value)
    return session


def a_level(seconds: float, high: bool, sequence: int) -> PinChange:
    """One level the chip select took."""
    return PinChange(
        pin=SELECT.identifier.value,
        level=SignalLevel.HIGH if high else SignalLevel.LOW,
        microseconds=int(seconds * SECOND),
        sequence=sequence,
    )


SELECT = GpioPinState(
    identifier=PinIdentifier(value=1, label="SPI_CS"),
    direction=PinDirection.OUTPUT,
    level=SignalLevel.HIGH,
    polarity=ActivePolarity.ACTIVE_LOW,
)


def test_a_pin_becomes_a_row_of_stretches_rather_than_moments() -> None:
    """A logic analyser draws bands; it was low from here to there."""
    session = a_session(
        pin_changes=(a_level(1.0, True, 0), a_level(1.5, False, 1), a_level(2.0, True, 2))
    )

    view = ObserveTimeline(session).execute()

    rows = [lane for lane in view.lanes if lane.kind == "digital"]
    assert rows[0].label == "SPI_CS"
    assert [mark.is_high for mark in rows[0].marks] == [True, False, True]
    assert rows[0].marks[0].duration_seconds == 0.5


def test_the_last_stretch_reaches_the_end_of_the_window() -> None:
    """A pin that is still high must not look like one that stopped."""
    session = a_session(pin_changes=(a_level(1.0, True, 0),))

    view = ObserveTimeline(session, window_seconds=5.0).execute()

    row = next(lane for lane in view.lanes if lane.kind == "digital")
    assert row.marks[-1].seconds + row.marks[-1].duration_seconds == view.window.end_seconds


def test_a_pin_nothing_was_recorded_for_is_not_a_row() -> None:
    """Nothing known is not the same as low, and is not drawn as low."""
    view = ObserveTimeline(a_session()).execute()

    assert [lane for lane in view.lanes if lane.kind == "digital"] == []


def test_the_level_a_pin_held_when_the_window_opened_survives() -> None:
    """Dropping it would leave the row blank until the pin next moved."""
    session = a_session(pin_changes=(a_level(1.0, False, 0), a_level(9.5, True, 1)))

    view = ObserveTimeline(session, window_seconds=2.0).execute()

    row = next(lane for lane in view.lanes if lane.kind == "digital")
    assert [mark.is_high for mark in row.marks] == [False, True]


def test_a_pin_and_a_bus_land_on_the_same_ruler() -> None:
    """The whole question: did the select go low before the first frame."""
    session = a_session(
        pin_changes=(a_level(2.0, False, 0),),
        exchanges=(an_exchange(2.1, 0),),
    )

    view = ObserveTimeline(session).execute()

    digital = next(lane for lane in view.lanes if lane.kind == "digital")
    bus = next(lane for lane in view.lanes if lane.marks and lane.kind == "bus")
    assert digital.marks[0].seconds < bus.marks[0].seconds
