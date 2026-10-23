"""What was measured at the adapter boundary.

Two questions, one measurement. How often was a call made and how long did
it take -- which says what the simulation costs and which model became
expensive. And how often did anything actually answer it -- which says what
the simulation is pretending.

The second is the one that finds bugs. A firmware that calls
``adapter_can_init`` and is handed ``false`` because nothing implements it
will fail its own start up, and the failure will look like a firmware bug
rather than a missing device model. That difference is the gap between the
calls and the ones something answered.

The durations are host time, not the time a call would take on the target.
Nothing here pretends otherwise: a simulated converter answering over a
function call has nothing in common with a real one answering over SPI.
The firmware's own timing is a different question, and the journal's
simulated timestamps answer it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from looper.domain.model.measurement import Distribution
from looper.domain.model.simulation.duration import (
    NANOSECONDS_PER_SECOND,
    duration_text,
)


@dataclass(frozen=True)
class CallTiming:
    """What was measured of one function at the adapter boundary.

    Attributes:
        function: Name of the function, or of the firmware loop itself.
        calls: How often it was called.
        answered_calls: How often something implemented the call: a hook,
            or a binding generated from a contract role.
        total_nanoseconds: Host time spent inside it, in total.
        shortest_nanoseconds: The quickest call.
        longest_nanoseconds: The slowest call.
        spread: How the calls were distributed across bands of
            duration. Empty for a measurement that did not count
            them, which is not the same as a function never called.
    """

    function: str
    calls: int
    answered_calls: int
    total_nanoseconds: int
    shortest_nanoseconds: int
    longest_nanoseconds: int
    spread: Distribution = field(default_factory=Distribution)

    def __post_init__(self) -> None:
        if self.answered_calls > self.calls:
            raise ValueError(
                f"'{self.function}' answered {self.answered_calls} of {self.calls} calls, "
                f"which is more than were made"
            )
        for name in ("calls", "total_nanoseconds"):
            if getattr(self, name) < 0:
                raise ValueError(f"A {name.replace('_', ' ')} count must not be negative")

    @property
    def mean_nanoseconds(self) -> float:
        """Host time one call took on average, or zero when never called."""
        return self.total_nanoseconds / self.calls if self.calls else 0.0

    @property
    def total_seconds(self) -> float:
        """Host time spent inside it, in seconds."""
        return self.total_nanoseconds / NANOSECONDS_PER_SECOND

    @property
    def unanswered_calls(self) -> int:
        """Calls that fell through to the zero value."""
        return self.calls - self.answered_calls

    @property
    def is_never_answered(self) -> bool:
        """Whether nothing implements this call at all.

        The firmware asked and was told nothing, every time. On a board
        that would be a missing driver; here it is a missing device model.
        """
        return self.calls > 0 and self.answered_calls == 0

    @property
    def is_partly_answered(self) -> bool:
        """Whether a hook appeared or disappeared while the firmware ran."""
        return 0 < self.answered_calls < self.calls

    @property
    def display_mean(self) -> str:
        """Average duration as clients show it."""
        return duration_text(self.mean_nanoseconds)

    @property
    def display_longest(self) -> str:
        """Slowest call as clients show it."""
        return duration_text(float(self.longest_nanoseconds))
