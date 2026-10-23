"""Use case that takes one snapshot of a running simulation."""

from __future__ import annotations

from looper.application.dto.simulation_view import SimulationView
from looper.application.mapping.simulation_view import build_simulation_view
from looper.domain.ports import SimulationSession


class ObserveSimulation:
    """Reads the state a client displays: elapsed time and every pin.

    Both values are read in one use case so that a client sees a consistent
    pair rather than a time from one moment and pins from another.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self) -> SimulationView:
        """Take one snapshot of the simulation."""
        time = self._session.read_time()
        pins = self._session.read_gpio_pins()
        return build_simulation_view(time, self._session.time_mode, pins)
