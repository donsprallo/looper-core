"""Data transfer objects describing what the adapter boundary cost."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CallTimingView(BaseModel):
    """What was measured of one function, ready to be drawn.

    Attributes:
        function: Name of the function, or of the firmware loop itself.
        calls: How often it was called.
        answered_calls: How often something implemented the call.
        total_seconds: Host time spent inside it.
        mean: Average duration, as it is shown.
        longest: Slowest call, as it is shown.
        is_never_answered: Whether every call fell through to the zero value.
        bands: How many calls fell into each band of duration, band
            n holding everything from 2^n nanoseconds up to 2^(n+1).
            Empty when nothing counted them.
        shape: What the spread amounts to, in a few words, or empty
            when there is nothing to say about it.
        origin: Which part of the simulation the function belongs to.
            Adapter functions are measured at the boundary, where the
            generated code stands; everything else is measured by the
            profiler, which is why a build without instrumentation shows
            the adapter alone.
    """

    model_config = ConfigDict(frozen=True)

    function: str
    calls: int
    answered_calls: int
    total_seconds: float
    mean: str
    longest: str
    is_never_answered: bool
    bands: tuple[int, ...] = ()
    shape: str = ""
    origin: str = "adapter"

    @property
    def unanswered_calls(self) -> int:
        """Calls that were handed the zero value."""
        return self.calls - self.answered_calls

    @property
    def is_spread_known(self) -> bool:
        """Whether anything counted how the calls were distributed."""
        return any(self.bands)


class TimingReportView(BaseModel):
    """Everything measured, and what it adds up to.

    Attributes:
        entries: One per function, heaviest first.
    """

    model_config = ConfigDict(frozen=True)

    entries: tuple[CallTimingView, ...]

    @property
    def heaviest_seconds(self) -> float:
        """Host time of the heaviest entry, which scales a chart."""
        return max((entry.total_seconds for entry in self.entries), default=0.0)

    @property
    def unanswered(self) -> tuple[CallTimingView, ...]:
        """The calls nothing implements, which is what to look at first."""
        return tuple(entry for entry in self.entries if entry.is_never_answered)
