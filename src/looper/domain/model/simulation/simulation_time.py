"""Point in time inside a running simulation."""

from __future__ import annotations

from dataclasses import dataclass

MICROSECONDS_PER_MILLISECOND = 1_000
MICROSECONDS_PER_SECOND = 1_000_000


@dataclass(frozen=True, order=True)
class SimulationTime:
    """Elapsed firmware time measured from simulation start.

    Attributes:
        microseconds: Elapsed microseconds since the simulation started.
    """

    microseconds: int

    def __post_init__(self) -> None:
        if self.microseconds < 0:
            raise ValueError("Simulation time must not be negative")

    @property
    def milliseconds(self) -> int:
        """Elapsed whole milliseconds, matching the ``millis()`` adapter API."""
        return self.microseconds // MICROSECONDS_PER_MILLISECOND

    @property
    def seconds(self) -> float:
        """Elapsed time in seconds, for display purposes."""
        return self.microseconds / MICROSECONDS_PER_SECOND

    def advanced_by(self, microseconds: int) -> SimulationTime:
        """Return the time reached after waiting for the given duration.

        Raises:
            ValueError: If the duration is negative.
        """
        if microseconds < 0:
            raise ValueError("A simulation time step must not be negative")
        return SimulationTime(self.microseconds + microseconds)
