"""Expecting things of a run, and what the report says when they fail.

A check that only says "failed" sends someone back to the simulation with
prints. Every outcome here carries what was expected and what was seen, so
these tests are as much about the wording of a failure as about the
arithmetic behind it.
"""

from __future__ import annotations

import pytest
from simulation_doubles import RecordingSession

from looper.application.expectations import Expectations
from looper.domain.model.simulation import (
    AnalogSample,
    BusAddress,
    BusDirection,
    BusKind,
    BusTraceEntry,
    CallTiming,
)


def samples_of(channel: int, values: tuple[float, ...]) -> tuple[AnalogSample, ...]:
    """One channel's samples, a millisecond apart."""
    return tuple(
        AnalogSample(channel=channel, microseconds=index * 1_000, value=value, sequence=index)
        for index, value in enumerate(values)
    )


def a_timing(function: str, calls: int, answered: int) -> CallTiming:
    """One measured function."""
    return CallTiming(
        function=function,
        calls=calls,
        answered_calls=answered,
        total_nanoseconds=calls * 100,
        shortest_nanoseconds=100,
        longest_nanoseconds=100,
    )


def an_exchange(sequence: int, accepted: bool = True) -> BusTraceEntry:
    """One recorded CAN frame on bus two."""
    return BusTraceEntry(
        bus=2,
        kind=BusKind.CAN,
        direction=BusDirection.OUTBOUND,
        address=BusAddress(BusKind.CAN, 0x701),
        payload=b"\x01",
        accepted=accepted,
        sequence=sequence,
    )


@pytest.fixture
def session() -> RecordingSession:
    """A session that has already recorded a second of a run."""
    built = RecordingSession()
    built.samples = samples_of(0, (0.0, 0.5, 1.0, 1.0))
    built.exchanges = (an_exchange(0), an_exchange(1))
    built.timings = (a_timing("adapter_spi_transfer_blocking", 8000, 8000),)
    built.advanced = 0
    return built


def test_a_channel_inside_its_range_passes(session: RecordingSession) -> None:
    check = Expectations(session)
    check.channel(0, "P1A").stays_between(0.0, 2.0)

    assert check.evaluate(for_seconds=1.0)


def test_a_channel_outside_its_range_says_what_it_reached(
    session: RecordingSession,
) -> None:
    check = Expectations(session)
    check.channel(0, "P1A").stays_between(0.0, 0.7)

    report = check.evaluate(for_seconds=1.0)

    assert not report
    assert "saw 0 .. 1 over 4 samples" in report.failures[0].line


def test_a_channel_that_was_never_recorded_fails_rather_than_passing(
    session: RecordingSession,
) -> None:
    """An expectation nothing could test is not an expectation that was met."""
    check = Expectations(session)
    check.channel(99, "absent").stays_between(0.0, 1.0)

    assert "nothing recorded" in check.evaluate(for_seconds=1.0).failures[0].line


def test_a_channel_that_arrives_in_time_passes(session: RecordingSession) -> None:
    check = Expectations(session)
    check.channel(0, "P1A").reaches(1.0, tolerance=0.01, within_seconds=0.01)

    assert check.evaluate(for_seconds=1.0)


def test_a_channel_that_arrives_too_late_says_how_long_it_took(
    session: RecordingSession,
) -> None:
    check = Expectations(session)
    check.channel(0, "P1A").reaches(1.0, tolerance=0.01, within_seconds=0.001)

    assert "reached after 0.002 s" in check.evaluate(for_seconds=1.0).failures[0].line


def test_a_channel_that_never_arrives_says_how_close_it_came(
    session: RecordingSession,
) -> None:
    check = Expectations(session)
    check.channel(0, "P1A").reaches(5.0, tolerance=0.01)

    assert "never closer than 1" in check.evaluate(for_seconds=1.0).failures[0].line


def test_a_bus_nothing_refused_passes(session: RecordingSession) -> None:
    check = Expectations(session)
    check.bus(2, "CAN2").nothing_refused()

    assert check.evaluate(for_seconds=1.0)


def test_a_refused_exchange_names_the_address(session: RecordingSession) -> None:
    session.exchanges = (an_exchange(0), an_exchange(1, accepted=False))
    check = Expectations(session)
    check.bus(2, "CAN2").nothing_refused()

    assert "1 of 2 refused at 0x701" in check.evaluate(for_seconds=1.0).failures[0].line


def test_a_call_that_was_answered_passes(session: RecordingSession) -> None:
    check = Expectations(session)
    check.call("adapter_spi_transfer_blocking").was_answered()

    assert check.evaluate(for_seconds=1.0)


def test_a_call_nothing_answers_is_the_failure_it_should_be(
    session: RecordingSession,
) -> None:
    """The firmware was handed the zero value and believed it."""
    session.timings = (a_timing("adapter_can_init", 1, 0),)
    check = Expectations(session)
    check.call("adapter_can_init").was_answered()

    assert "0 of 1 answered" in check.evaluate(for_seconds=1.0).failures[0].line


def test_a_call_that_never_happened_is_reported_as_such(
    session: RecordingSession,
) -> None:
    check = Expectations(session)
    check.call("adapter_flash_erase").was_answered()

    assert "never called" in check.evaluate(for_seconds=1.0).failures[0].line


def test_a_rate_is_worked_out_from_the_time_that_passed(
    session: RecordingSession,
) -> None:
    check = Expectations(session)
    check.call("adapter_spi_transfer_blocking").happened_at(8000, tolerance=0.05)

    assert check.evaluate(for_seconds=1.0)


def test_a_rate_that_is_wrong_says_what_it_measured(session: RecordingSession) -> None:
    check = Expectations(session)
    check.call("adapter_spi_transfer_blocking").happened_at(100.0, tolerance=0.05)

    assert "saw 8000 Hz" in check.evaluate(for_seconds=1.0).failures[0].line


def test_a_firmware_making_no_calls_at_all_is_caught(session: RecordingSession) -> None:
    session.timings = ()
    check = Expectations(session)
    check.firmware_is_alive()

    assert not check.evaluate(for_seconds=1.0)


def test_the_recordings_are_cleared_before_the_window(
    session: RecordingSession,
) -> None:
    """A check must see its own window, not whatever happened before it."""
    Expectations(session).firmware_is_alive().evaluate(for_seconds=1.0)

    assert session.cleared == ["trace", "bus trace", "timings", "profile", "heap"]


def test_the_report_lists_the_failures_first(session: RecordingSession) -> None:
    check = Expectations(session)
    check.firmware_is_alive()
    check.channel(0, "P1A").stays_between(0.0, 0.1)

    summary = check.evaluate(for_seconds=1.0).summary

    assert summary.splitlines()[0] == "1 of 2 met"
    assert summary.splitlines()[1].startswith("FAIL")


def test_nothing_expected_is_said_rather_than_silently_passing(
    session: RecordingSession,
) -> None:
    assert Expectations(session).evaluate(for_seconds=1.0).summary == "nothing was expected"
