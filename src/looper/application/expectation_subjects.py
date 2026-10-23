"""What an expectation is about, before it says what it expects.

`check.channel(0, "P1A").reaches(1.0)` reads as a sentence because the
subject and the claim are separate objects. These are the subjects;
the claims they make are the checks.

Each of them only collects: nothing here reads the simulation, and
nothing is evaluated until the window has passed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from looper.application.expectation_checks import (
    BusCarriedAtLeast,
    BusNothingRefused,
    CallHappened,
    CallRate,
    CallWasAnswered,
    ChannelReaches,
    ChannelStaysBetween,
)
from looper.application.expectation_memory import (
    HeapStaysBelow,
    NeverAllocates,
    NothingLeaked,
    StackNoDeeperThan,
    StackStaysBelow,
)

if TYPE_CHECKING:
    from looper.application.expectations import Expectations


class ChannelExpectation:
    """What is expected of one analog channel."""

    def __init__(self, expectations: Expectations, channel_id: int, name: str) -> None:
        self._expectations = expectations
        self._channel_id = channel_id
        self._name = name

    def stays_between(self, low: float, high: float) -> Expectations:
        """Expect every recorded sample to be within a range."""
        return self._expectations.add(ChannelStaysBetween(self._channel_id, self._name, low, high))

    def reaches(
        self, value: float, tolerance: float = 0.0, within_seconds: float = float("inf")
    ) -> Expectations:
        """Expect the channel to arrive at a value, and in time."""
        return self._expectations.add(
            ChannelReaches(self._channel_id, self._name, value, tolerance, within_seconds)
        )


class BusExpectation:
    """What is expected of one bus."""

    def __init__(self, expectations: Expectations, bus_id: int, name: str) -> None:
        self._expectations = expectations
        self._bus_id = bus_id
        self._name = name

    def nothing_refused(self) -> Expectations:
        """Expect everything that crossed to have been taken by something."""
        return self._expectations.add(BusNothingRefused(self._bus_id, self._name))

    def carried_at_least(self, count: int) -> Expectations:
        """Expect at least so many exchanges."""
        return self._expectations.add(BusCarriedAtLeast(self._bus_id, self._name, count))


class CallExpectation:
    """What is expected of one adapter function."""

    def __init__(self, expectations: Expectations, function: str) -> None:
        self._expectations = expectations
        self._function = function

    def happened_at_least(self, count: int) -> Expectations:
        """Expect the firmware to have called it at least so many times."""
        return self._expectations.add(CallHappened(self._function, count))

    def was_answered(self) -> Expectations:
        """Expect something to implement it, rather than the zero value."""
        return self._expectations.add(CallWasAnswered(self._function))

    def happened_at(self, hertz: float, tolerance: float = 0.05) -> Expectations:
        """Expect it to have been called at about a given rate."""
        return self._expectations.add(CallRate(self._function, hertz, tolerance))


class MemoryExpectation:
    """What is expected of the heap."""

    def __init__(self, expectations: Expectations) -> None:
        self._expectations = expectations

    def never_allocates(self) -> Expectations:
        """Expect nothing to have asked the allocator for anything."""
        return self._expectations.add(NeverAllocates())

    def peak_below(self, bytes_allowed: int) -> Expectations:
        """Expect the heap never to have held more than so many bytes."""
        return self._expectations.add(HeapStaysBelow(bytes_allowed))

    def nothing_leaked(self) -> Expectations:
        """Expect everything taken over the window to have been given back."""
        return self._expectations.add(NothingLeaked())


class StackExpectation:
    """What is expected of the stack."""

    def __init__(self, expectations: Expectations) -> None:
        self._expectations = expectations

    def stays_below(self, bytes_allowed: int) -> Expectations:
        """Expect the stack never to have gone past so many host bytes."""
        return self._expectations.add(StackStaysBelow(bytes_allowed))

    def no_deeper_than(self, frames_allowed: int) -> Expectations:
        """Expect the calls never to have nested more than so deep."""
        return self._expectations.add(StackNoDeeperThan(frames_allowed))
