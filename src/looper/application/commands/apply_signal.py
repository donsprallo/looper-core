"""Use case that drives an analog input with a generated signal."""

from __future__ import annotations

from looper.domain.model.simulation import SignalDefinition, Waveform
from looper.domain.ports import SimulationSession


class ApplySignal:
    """Installs the signal that drives one analog input.

    The signal is evaluated inside the simulation on every firmware read, so
    the firmware sees it at its own sampling rate rather than at the rate a
    client could send samples.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self, channel_id: int, signal: SignalDefinition) -> None:
        """Drive a channel with the given signal.

        Raises:
            ValueError: If the channel is unknown or the firmware drives it.
        """
        self._session.set_signal(channel_id, signal)

    def apply_constant(self, channel_id: int, level: float) -> None:
        """Hold a channel at a constant level, which is a DC signal.

        Raises:
            ValueError: If the channel is unknown or the firmware drives it.
        """
        self.execute(channel_id, SignalDefinition(waveform=Waveform.CONSTANT, offset=level))
