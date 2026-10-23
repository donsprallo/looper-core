"""Observable state of a simulated general purpose IO pin."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

from looper.domain.model.simulation.pin_identifier import PinIdentifier


@unique
class PinDirection(Enum):
    """Whether the firmware drives a pin or reads it."""

    INPUT = "input"
    OUTPUT = "output"


@unique
class SignalLevel(Enum):
    """Electrical level present at a pin."""

    LOW = "low"
    HIGH = "high"

    @property
    def inverted(self) -> SignalLevel:
        """The opposite electrical level."""
        return SignalLevel.LOW if self is SignalLevel.HIGH else SignalLevel.HIGH


@unique
class ActivePolarity(Enum):
    """Which electrical level the firmware treats as active."""

    ACTIVE_HIGH = "active_high"
    ACTIVE_LOW = "active_low"

    def level_for_active(self) -> SignalLevel:
        """The electrical level that means active for this polarity."""
        return SignalLevel.HIGH if self is ActivePolarity.ACTIVE_HIGH else SignalLevel.LOW


@dataclass(frozen=True)
class GpioPinState:
    """A pin as a client observes and manipulates it.

    Attributes:
        identifier: Identity of the pin.
        direction: Whether the firmware drives or reads the pin.
        level: Current electrical level.
        polarity: Which level the firmware treats as active.
    """

    identifier: PinIdentifier
    direction: PinDirection
    level: SignalLevel
    polarity: ActivePolarity = ActivePolarity.ACTIVE_HIGH

    @property
    def is_active(self) -> bool:
        """Whether the current level means active for the configured polarity."""
        return self.level is self.polarity.level_for_active()

    @property
    def is_drivable_by_client(self) -> bool:
        """Whether a client may set the level, which only applies to inputs."""
        return self.direction is PinDirection.INPUT

    def with_level(self, level: SignalLevel) -> GpioPinState:
        """Return the same pin at a different electrical level."""
        return GpioPinState(
            identifier=self.identifier,
            direction=self.direction,
            level=level,
            polarity=self.polarity,
        )

    def toggled(self) -> GpioPinState:
        """Return the same pin at the opposite electrical level."""
        return self.with_level(self.level.inverted)
