"""The things one can expect of a firmware's memory.

Two of these are rules a project already has and keeps by reading the
code: this firmware does not allocate once it is up, and this firmware
does not leak. Both become measurements here, which is the whole point
of running the thing on a host.

The third is the stack, and it needs reading with the care the rest of
this says. The depth is the firmware's own and means the same on a
target. The bytes are this machine's, and a limit set against them is
a limit on the simulation rather than on the board -- useful for
noticing that something changed, not for signing anything off.
"""

from __future__ import annotations

from dataclasses import dataclass

from looper.application.expectation_checks import Check
from looper.application.expectation_observation import Observation
from looper.domain.model.testing import Outcome

NOT_WATCHED = "the allocator is not being watched in this build"
NOT_MEASURED = "nothing instrumented ran in this build"


@dataclass(frozen=True)
class NeverAllocates(Check):
    """Nothing asked the allocator for anything."""

    def evaluate(self, observed: Observation) -> Outcome:
        """Count what passed through the allocator over the window."""
        heap = observed.heap
        if not heap.is_watched:
            return Outcome("the heap", "no allocation at all", NOT_WATCHED, met=False)
        seen = f"{heap.allocations} allocations"
        return Outcome("the heap", "no allocation at all", seen, met=heap.allocations == 0)


@dataclass(frozen=True)
class HeapStaysBelow(Check):
    """The heap never held more than so many bytes at once."""

    bytes_allowed: int

    def evaluate(self, observed: Observation) -> Outcome:
        """Compare the peak against what is allowed."""
        heap = observed.heap
        expected = f"at most {self.bytes_allowed} bytes out at once"
        if not heap.is_watched:
            return Outcome("the heap", expected, NOT_WATCHED, met=False)
        return Outcome(
            "the heap",
            expected,
            f"{heap.peak_bytes} bytes at the peak",
            met=heap.peak_bytes <= self.bytes_allowed,
        )


@dataclass(frozen=True)
class NothingLeaked(Check):
    """Everything allocated over the window was given back.

    Over the window, not over all time: a block the firmware took
    before the window began is not a leak, and counting it as one
    would make this fail for the C runtime's own buffers.
    """

    def evaluate(self, observed: Observation) -> Outcome:
        """Compare what was taken against what was given back."""
        heap = observed.heap
        if not heap.is_watched:
            return Outcome("the heap", "everything freed again", NOT_WATCHED, met=False)
        kept = heap.allocations - heap.frees
        seen = f"{heap.allocations} allocated, {heap.frees} freed"
        return Outcome("the heap", "everything freed again", seen, met=kept <= 0)


@dataclass(frozen=True)
class StackStaysBelow(Check):
    """The stack never went deeper than so many bytes."""

    bytes_allowed: int

    def evaluate(self, observed: Observation) -> Outcome:
        """Compare the high water mark against what is allowed."""
        expected = f"at most {self.bytes_allowed} bytes of stack"
        if observed.stack_depth == 0:
            return Outcome("the stack", expected, NOT_MEASURED, met=False)
        return Outcome(
            "the stack",
            expected,
            f"{observed.stack_bytes} bytes at the deepest",
            met=observed.stack_bytes <= self.bytes_allowed,
        )


@dataclass(frozen=True)
class StackNoDeeperThan(Check):
    """The calls never nested more than so many deep.

    The one memory figure that carries over unchanged: a firmware that
    nests twenty two calls here nests twenty two there.
    """

    frames_allowed: int

    def evaluate(self, observed: Observation) -> Outcome:
        """Compare the deepest nesting against what is allowed."""
        expected = f"at most {self.frames_allowed} frames"
        if observed.stack_depth == 0:
            return Outcome("the stack", expected, NOT_MEASURED, met=False)
        return Outcome(
            "the stack",
            expected,
            f"{observed.stack_depth} frames at the deepest",
            met=observed.stack_depth <= self.frames_allowed,
        )
