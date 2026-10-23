"""Use case that applies an electrical level to a simulated input pin."""

from __future__ import annotations

from looper.domain.model.simulation import PinIdentifier, SignalLevel
from looper.domain.ports import SimulationSession


class DrivePin:
    """Drives one pin the firmware reads.

    The check that a pin is drivable lives in the domain model, so a client
    that forgets to disable a control cannot drive an output by accident.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self, pin_id: int, level: SignalLevel) -> None:
        """Apply a level to the pin with the given number.

        Raises:
            ValueError: If the pin is unknown or the firmware drives it.
        """
        identifier = PinIdentifier(value=pin_id)
        self._session.drive_input_pin(identifier, level)

    def toggle(self, pin_id: int, current: SignalLevel) -> SignalLevel:
        """Apply the opposite of the current level and report what was set.

        Raises:
            ValueError: If the pin is unknown or the firmware drives it.
        """
        level = current.inverted
        self.execute(pin_id, level)
        return level
