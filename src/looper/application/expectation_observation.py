"""Everything the checks are allowed to look at, taken once per run.

Gathered in one place and handed to every check, so that twenty
expectations cost one reading of each recording rather than twenty --
and so that all twenty are looking at the same window rather than at
twenty slightly different ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from looper.application.dto import BusTraceView, TimingReportView, TraceView
from looper.domain.model.memory import HeapReading


def _loss_note(lost: int) -> str:
    """Say that the recording overflowed, when it did."""
    return f", and {lost} more the recording could not keep" if lost > 0 else ""


@dataclass(frozen=True)
class Observation:
    """Everything the checks are allowed to look at, taken once per run.

    Gathered in one place so that twenty expectations cost one read of
    each recording rather than twenty.

    Attributes:
        trace: The analog samples recorded over the window.
        exchanges: What crossed the buses over the window.
        timings: What the adapter boundary cost, since it was last reset.
        elapsed_seconds: Simulated time the window covered.
        lost_samples: Samples the recording could not keep. A fast channel
            fills a ring faster than any client empties it, and a check
            that pretended otherwise would quietly measure the ring.
        lost_exchanges: The same, for what crossed the buses.
        heap: What passed through the allocator, which is nothing at
            all in a build that is not watching it.
        stack_bytes: Host stack in use at the deepest moment.
        stack_depth: Frames on the stack at that moment, which is zero
            when this build was not woven for a profile.
    """

    trace: TraceView
    exchanges: BusTraceView
    timings: TimingReportView
    elapsed_seconds: float
    lost_samples: int = 0
    lost_exchanges: int = 0
    heap: HeapReading = field(default_factory=HeapReading)
    stack_bytes: int = 0
    stack_depth: int = 0

    @property
    def sample_loss_note(self) -> str:
        """What to add to an observation when samples were discarded."""
        return _loss_note(self.lost_samples)

    @property
    def exchange_loss_note(self) -> str:
        """What to add to an observation when exchanges were discarded."""
        return _loss_note(self.lost_exchanges)
