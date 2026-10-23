"""Expecting things of a running firmware, and finding out.

A firmware test has two halves. Setting the scene -- driving an input,
putting a frame on a bus -- which is what the rest of this package is for,
and saying what should then be true, which is this.

Expectations are declared first and checked afterwards, against one window
of time. That ordering is what lets twenty of them cost one reading of
each recording, and it is also what lets a check look at the whole window
rather than at the instant it happened to run.

In virtual time the window is advanced rather than waited out, so a test
takes as long as the firmware needs and not a second more, and two runs
see the same thing.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from looper.application.expectation_checks import Check, FirmwareIsAlive
from looper.application.expectation_observation import Observation
from looper.application.expectation_subjects import (
    BusExpectation,
    CallExpectation,
    ChannelExpectation,
    MemoryExpectation,
    StackExpectation,
)
from looper.application.mapping.analog_view import build_trace_view
from looper.application.mapping.bus_view import build_bus_trace_view
from looper.application.mapping.timing_view import build_timing_report_view
from looper.domain.model.simulation import TimeMode
from looper.domain.model.testing import ExpectationReport
from looper.domain.ports import SimulationSession

MICROSECONDS_PER_SECOND = 1_000_000

#: Pages one reading will take before giving up. A window long enough to
#: need more than this is long enough that a check should say so.
MAXIMUM_PAGES = 512


class Expectations:
    """Collects what should be true, then finds out whether it is.

    Declare, then evaluate::

        check = Expectations(session)
        check.channel(0, "P1A").reaches(1.0, tolerance=0.01, within_seconds=0.2)
        check.call("adapter_spi_dma_transfer").happened_at(8000)
        check.bus(2, "CAN2").nothing_refused()

        assert check.evaluate(for_seconds=1.0)
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session
        self._checks: list[Check] = []

    def add(self, check: Check) -> Expectations:
        """Take one more expectation, and allow another to be chained."""
        self._checks.append(check)
        return self

    def channel(self, channel_id: int, name: str = "") -> ChannelExpectation:
        """Expect something of one analog channel."""
        return ChannelExpectation(self, channel_id, name or f"channel {channel_id}")

    def bus(self, bus_id: int, name: str = "") -> BusExpectation:
        """Expect something of one bus."""
        return BusExpectation(self, bus_id, name or f"bus {bus_id}")

    def call(self, function: str) -> CallExpectation:
        """Expect something of one adapter function."""
        return CallExpectation(self, function)

    def memory(self) -> MemoryExpectation:
        """Expect something of the heap."""
        return MemoryExpectation(self)

    def stack(self) -> StackExpectation:
        """Expect something of the stack."""
        return StackExpectation(self)

    def firmware_is_alive(self) -> Expectations:
        """Expect the firmware to still be reaching the adapter at all."""
        return self.add(FirmwareIsAlive())

    def evaluate(self, for_seconds: float = 1.0) -> ExpectationReport:
        """Watch for a while, then check everything that was declared.

        The recordings are cleared first, so a check sees the window and
        not whatever happened before it.
        """
        self._begin()
        elapsed = self._let_time_pass(for_seconds)
        observed = self._observe(elapsed)
        return ExpectationReport(outcomes=tuple(check.evaluate(observed) for check in self._checks))

    def _begin(self) -> None:
        """Clear what is about to be measured."""
        self._session.clear_trace()
        self._session.clear_bus_trace()
        self._session.clear_call_timings()
        self._session.clear_profile()
        self._session.clear_heap()

    def _let_time_pass(self, seconds: float) -> float:
        """Advance the clock, or wait, and report how much time passed.

        In virtual time the clock is told to move, which makes a test
        deterministic and as quick as the firmware allows. In real time
        there is nothing to do but wait.
        """
        before = self._session.read_time().microseconds
        if self._session.time_mode is TimeMode.VIRTUAL:
            self._session.advance_time(int(seconds * MICROSECONDS_PER_SECOND))
        else:
            time.sleep(seconds)
        after = self._session.read_time().microseconds
        return (after - before) / MICROSECONDS_PER_SECOND

    def _observe(self, elapsed_seconds: float) -> Observation:
        """Read every recording, to the end.

        One request carries a page, and a window of a fast channel is many
        pages. A check that counted one page would quietly measure the
        page size instead of the run, so the pages are read until they
        stop coming.
        """
        samples, next_sequence = _all_of(self._session.read_trace)
        exchanges, next_bus = _all_of(self._session.read_bus_trace)
        profile = self._session.read_profile(0)
        return Observation(
            trace=build_trace_view(samples, next_sequence),
            exchanges=build_bus_trace_view(exchanges, next_bus),
            timings=build_timing_report_view(self._session.read_call_timings()),
            elapsed_seconds=elapsed_seconds,
            lost_samples=max(0, next_sequence - len(samples)),
            lost_exchanges=max(0, next_bus - len(exchanges)),
            heap=self._session.read_heap(),
            stack_bytes=profile.deepest_stack_bytes,
            stack_depth=profile.deepest_depth,
        )


def _all_of[RecordT](
    read_page: Callable[[int], tuple[tuple[RecordT, ...], int]],
) -> tuple[tuple[RecordT, ...], int]:
    """Read pages until one comes back empty or stops moving forward.

    The guard on the sequence number is not belt and braces: a recording
    that has wrapped answers from its oldest held entry, and without it a
    reader that fell behind would ask for the same page for ever.
    """
    collected: list[RecordT] = []
    after = 0
    for _ in range(MAXIMUM_PAGES):
        page, next_sequence = read_page(after)
        collected.extend(page)
        if not page or next_sequence <= after:
            return tuple(collected), next_sequence
        after = next_sequence
    return tuple(collected), after
