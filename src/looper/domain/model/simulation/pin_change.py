"""One moment a pin took a new level.

The pin model says what every pin is now. That answers whether the
chip select is asserted and never answers the question a bus raises:
did it go low *before* the first clock. For that a reader needs the
moments, and a moment is this.

Changes only, which is what makes a logic analyser readable. A pin
the firmware polls a thousand times without touching contributes one
of these, not a thousand, and a slow signal is therefore still in the
recording after a fast one has been busy.
"""

from __future__ import annotations

from dataclasses import dataclass

from looper.domain.model.simulation.gpio_pin import SignalLevel

MICROSECONDS_PER_SECOND = 1_000_000.0


@dataclass(frozen=True)
class PinChange:
    """A pin, the level it took, and when.

    Attributes:
        pin: Opaque pin number the adapter addresses it by.
        level: Level it took at that moment.
        microseconds: Simulated time it took it.
        sequence: Position in the recording, used to read incrementally.
    """

    pin: int
    level: SignalLevel
    microseconds: int = 0
    sequence: int = 0

    def __post_init__(self) -> None:
        if self.microseconds < 0:
            raise ValueError("A pin cannot have changed at a negative time")

    @property
    def seconds(self) -> float:
        """Recording time in seconds, for lining up with everything else."""
        return self.microseconds / MICROSECONDS_PER_SECOND

    @property
    def is_high(self) -> bool:
        """Whether the pin went high rather than low."""
        return self.level is SignalLevel.HIGH
