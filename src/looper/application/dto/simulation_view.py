"""Data transfer objects describing a running simulation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PinView(BaseModel):
    """One pin as a client displays and manipulates it.

    Attributes:
        pin_id: Opaque pin number used by the firmware.
        name: Readable pin name, or the hexadecimal number when unlabelled.
        direction: Whether the firmware drives or reads the pin.
        level: Current electrical level.
        is_active: Whether the level means active for the configured polarity.
        is_drivable: Whether a client may change the level.
    """

    model_config = ConfigDict(frozen=True)

    pin_id: int
    name: str
    direction: str
    level: str
    is_active: bool
    is_drivable: bool


class SimulationView(BaseModel):
    """A snapshot of the simulation as a client sees it.

    Attributes:
        microseconds: Elapsed firmware time at the moment of the snapshot.
        time_mode: The time source the firmware was started with.
        pins: Every pin the firmware has registered.
    """

    model_config = ConfigDict(frozen=True)

    microseconds: int
    time_mode: str
    pins: tuple[PinView, ...]

    @property
    def milliseconds(self) -> int:
        """Elapsed whole milliseconds, matching the millis() adapter API."""
        return self.microseconds // 1000
