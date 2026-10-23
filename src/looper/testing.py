"""Expecting things of a running firmware, from a test.

The user facing name for what `looper.application.expectations` does::

    from looper.testing import Expectations
    from looper.infrastructure.ipc import ProtobufSimulationSession

    def test_a_shunt_drop_becomes_a_current():
        session = ProtobufSimulationSession(port=45771)
        session.set_signal(10, SignalDefinition(offset=0.001))

        check = Expectations(session)
        check.channel(0, "P1A").reaches(1.0, tolerance=0.01, within_seconds=0.5)
        check.call("adapter_can_init").was_answered()
        check.memory().never_allocates()
        check.stack().no_deeper_than(32)
        check.firmware_is_alive()

        report = check.evaluate(for_seconds=1.0)
        assert report, report.summary
"""

from __future__ import annotations

from looper.application.expectation_subjects import (
    BusExpectation,
    CallExpectation,
    ChannelExpectation,
    MemoryExpectation,
    StackExpectation,
)
from looper.application.expectations import Expectations
from looper.domain.model.testing import ExpectationReport, Outcome

__all__ = [
    "BusExpectation",
    "CallExpectation",
    "ChannelExpectation",
    "ExpectationReport",
    "Expectations",
    "MemoryExpectation",
    "StackExpectation",
    "Outcome",
]
