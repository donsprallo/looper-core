"""Mapping of simulation state onto the client facing snapshot."""

from __future__ import annotations

from looper.application.dto.simulation_view import PinView, SimulationView
from looper.domain.model.simulation import GpioPinState, SimulationTime, TimeMode


def build_simulation_view(
    time: SimulationTime, mode: TimeMode, pins: tuple[GpioPinState, ...]
) -> SimulationView:
    """Translate the observed simulation state into a snapshot."""
    return SimulationView(
        microseconds=time.microseconds,
        time_mode=mode.value,
        pins=tuple(_build_pin(pin) for pin in pins),
    )


def _build_pin(pin: GpioPinState) -> PinView:
    """Translate one observed pin into its view."""
    return PinView(
        pin_id=pin.identifier.value,
        name=pin.identifier.display_name,
        direction=pin.direction.value,
        level=pin.level.value,
        is_active=pin.is_active,
        is_drivable=pin.is_drivable_by_client,
    )
