"""What was measured of one function anywhere in the simulation.

Two durations, and the difference between them is the point. The total
is everything that happened between entering a function and leaving it,
including what it called. The self time is what is left when the calls
it made are taken away, which is the time the function itself spent.

A caller with a large total and a small self time is a conductor. A
function with a large self time is doing the work -- or is calling
something that was never instrumented, a library routine say, in which
case that library time has nowhere else to appear and lands here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from looper.domain.model.simulation.duration import (
    NANOSECONDS_PER_SECOND,
    duration_text,
)
from looper.domain.model.sources.function_origin import FunctionOrigin

UNKNOWN_NAME_PREFIX = "unnamed at "


@dataclass(frozen=True)
class ProfiledFunction:
    """What was measured of one function over one window.

    Attributes:
        name: Name the debug information gives it.
        origin: Which part of the simulation it belongs to.
        source: File it was compiled from, empty when nothing says.
        calls: How often it was entered.
        total_nanoseconds: Host time between entering and leaving, with
            everything it called included.
        self_nanoseconds: The same with the calls it made taken away.
        longest_nanoseconds: The slowest single call, including children.
    """

    name: str
    origin: FunctionOrigin
    source: PurePath | None = None
    calls: int = 0
    total_nanoseconds: int = 0
    self_nanoseconds: int = 0
    longest_nanoseconds: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("A profiled function has a name")
        if self.calls < 0:
            raise ValueError(f"'{self.name}' cannot have been called {self.calls} times")
        if self.self_nanoseconds > self.total_nanoseconds:
            raise ValueError(
                f"'{self.name}' spent more time in itself than in itself and everything it called"
            )

    @property
    def directory(self) -> str:
        """Where the function's source lives, as a report groups by it."""
        return str(self.source.parent) if self.source is not None else ""

    @property
    def file_name(self) -> str:
        """The source file alone, without the path to it."""
        return self.source.name if self.source is not None else ""

    @property
    def children_nanoseconds(self) -> int:
        """Host time spent in what this function called."""
        return self.total_nanoseconds - self.self_nanoseconds

    @property
    def mean_nanoseconds(self) -> float:
        """Host time one call took on average, or zero when never called."""
        return self.total_nanoseconds / self.calls if self.calls else 0.0

    @property
    def self_seconds(self) -> float:
        """Host time spent in the function itself, in seconds."""
        return self.self_nanoseconds / NANOSECONDS_PER_SECOND

    @property
    def display_total(self) -> str:
        """Total duration as clients show it."""
        return duration_text(float(self.total_nanoseconds))

    @property
    def display_self(self) -> str:
        """Self duration as clients show it."""
        return duration_text(float(self.self_nanoseconds))

    @property
    def display_mean(self) -> str:
        """Average duration as clients show it."""
        return duration_text(self.mean_nanoseconds)
