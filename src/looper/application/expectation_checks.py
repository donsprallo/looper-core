"""The individual things one can expect of a running firmware.

Each check reads what the simulation already records -- the analog trace,
the bus recording, the measurements at the adapter boundary -- and says
what it expected and what it saw. None of them makes the simulation do
anything; the scenario is the caller's, and these only look.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from looper.application.dto import CallTimingView
from looper.application.expectation_observation import Observation
from looper.domain.model.testing import Outcome

NOTHING_RECORDED = "nothing recorded"


class Check(ABC):
    """One thing expected of a run."""

    @abstractmethod
    def evaluate(self, observed: Observation) -> Outcome:
        """Say whether what was seen matches what was expected."""


@dataclass(frozen=True)
class ChannelStaysBetween(Check):
    """A channel never leaves a range."""

    channel_id: int
    name: str
    low: float
    high: float

    def evaluate(self, observed: Observation) -> Outcome:
        """Compare every recorded sample of the channel against the range."""
        values = [
            sample.value
            for sample in observed.trace.samples
            if sample.channel_id == self.channel_id
        ]
        expected = f"every sample within {self.low:g} .. {self.high:g}"
        if not values:
            return Outcome(self.name, expected, NOTHING_RECORDED, met=False)
        seen = (
            f"{min(values):g} .. {max(values):g} over {len(values)} samples"
            + observed.sample_loss_note
        )
        return Outcome(
            self.name, expected, seen, met=min(values) >= self.low and max(values) <= self.high
        )


@dataclass(frozen=True)
class ChannelReaches(Check):
    """A channel arrives at a value, and does so in time."""

    channel_id: int
    name: str
    value: float
    tolerance: float
    within_seconds: float

    def evaluate(self, observed: Observation) -> Outcome:
        """Find the first sample within tolerance, and say how long it took."""
        samples = [
            sample for sample in observed.trace.samples if sample.channel_id == self.channel_id
        ]
        expected = f"{self.value:g} +/- {self.tolerance:g} within {self.within_seconds:g} s"
        if not samples:
            return Outcome(self.name, expected, NOTHING_RECORDED, met=False)
        start = samples[0].seconds
        arrived = [sample for sample in samples if abs(sample.value - self.value) <= self.tolerance]
        if not arrived:
            closest = min(samples, key=lambda one: abs(one.value - self.value))
            return Outcome(self.name, expected, f"never closer than {closest.value:g}", met=False)
        took = arrived[0].seconds - start
        return Outcome(
            self.name, expected, f"reached after {took:.4g} s", met=took <= self.within_seconds
        )


@dataclass(frozen=True)
class BusNothingRefused(Check):
    """Everything that crossed a bus was taken by something."""

    bus_id: int
    name: str

    def evaluate(self, observed: Observation) -> Outcome:
        """Count what crossed the bus and what nothing took."""
        on_bus = [one for one in observed.exchanges.exchanges if one.bus_id == self.bus_id]
        refused = [one for one in on_bus if one.was_refused]
        addresses = ", ".join(sorted({one.address for one in refused}))
        seen = f"{len(refused)} of {len(on_bus)} refused" + (f" at {addresses}" if refused else "")
        return Outcome(self.name, "nothing refused", seen, met=not refused)


@dataclass(frozen=True)
class BusCarriedAtLeast(Check):
    """A bus carried at least so many exchanges."""

    bus_id: int
    name: str
    count: int

    def evaluate(self, observed: Observation) -> Outcome:
        """Count what crossed the bus."""
        on_bus = [one for one in observed.exchanges.exchanges if one.bus_id == self.bus_id]
        seen = f"{len(on_bus)}" + observed.exchange_loss_note
        return Outcome(
            self.name,
            f"at least {self.count} exchanges",
            seen,
            met=len(on_bus) + observed.lost_exchanges >= self.count,
        )


@dataclass(frozen=True)
class CallHappened(Check):
    """An adapter function was called at least so many times."""

    function: str
    count: int

    def evaluate(self, observed: Observation) -> Outcome:
        """Count how often the firmware made the call."""
        calls = _calls_of(observed, self.function)
        return Outcome(
            self.function, f"at least {self.count} calls", f"{calls}", met=calls >= self.count
        )


@dataclass(frozen=True)
class CallWasAnswered(Check):
    """Something implemented a call, rather than handing back the zero value."""

    function: str

    def evaluate(self, observed: Observation) -> Outcome:
        """Compare the calls made against the ones something answered."""
        entry = _entry_of(observed, self.function)
        if entry is None:
            return Outcome(self.function, "implemented and called", "never called", met=False)
        seen = f"{entry.answered_calls} of {entry.calls} answered"
        return Outcome(self.function, "every call answered", seen, met=not entry.unanswered_calls)


@dataclass(frozen=True)
class CallRate(Check):
    """An adapter function was called at about a given rate."""

    function: str
    hertz: float
    tolerance: float

    def evaluate(self, observed: Observation) -> Outcome:
        """Work the rate out of the calls and the time that passed."""
        calls = _calls_of(observed, self.function)
        expected = f"{self.hertz:g} Hz +/- {self.tolerance:.0%}"
        if observed.elapsed_seconds <= 0.0:
            return Outcome(self.function, expected, "no time passed", met=False)
        measured = calls / observed.elapsed_seconds
        allowed = self.hertz * self.tolerance
        return Outcome(
            self.function,
            expected,
            f"{measured:.4g} Hz",
            met=abs(measured - self.hertz) <= allowed,
        )


@dataclass(frozen=True)
class FirmwareIsAlive(Check):
    """The firmware is still reaching the adapter at all."""

    def evaluate(self, observed: Observation) -> Outcome:
        """Count every adapter call there was."""
        calls = sum(entry.calls for entry in observed.timings.entries)
        return Outcome("the firmware", "still calling the adapter", f"{calls} calls", met=calls > 0)


def _entry_of(observed: Observation, function: str) -> CallTimingView | None:
    """The measurements of one function, or None when it was never called."""
    for entry in observed.timings.entries:
        if entry.function == function:
            return entry
    return None


def _calls_of(observed: Observation, function: str) -> int:
    """How often one function was called."""
    entry = _entry_of(observed, function)
    return 0 if entry is None else int(entry.calls)
