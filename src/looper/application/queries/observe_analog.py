"""Use cases that read the analog side of a running simulation."""

from __future__ import annotations

from looper.application.dto.analog_view import ChannelView, TraceView
from looper.application.mapping.analog_view import build_channel_view, build_trace_view
from looper.domain.model.simulation import AnalogSample
from looper.domain.ports import SimulationSession


class ObserveChannels:
    """Reads every analog channel the firmware has registered."""

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self) -> tuple[ChannelView, ...]:
        """Take one snapshot of every channel."""
        return tuple(
            build_channel_view(channel) for channel in self._session.read_analog_channels()
        )


#: Replies one reading will take before giving up. A firmware at
#: sixteen thousand samples a second fills three of them between two
#: polls; a hundred is room for a client that was away for a while.
MAXIMUM_PAGES = 100


class ReadTrace:
    """Reads recorded samples incrementally.

    A plot needs every sample the firmware produced, not only the ones
    that happened to fall on a poll. One reply carries a few hundred
    samples and a firmware produces thousands a second, so a reading
    that took one reply would show a burst of signal and then a gap --
    and the gap would move, which looks exactly like a signal that
    cannot be plotted above a few hertz.

    So a reading keeps asking until it has caught up. The sequence a
    reply reports as next is where the *recording* has got to, not
    where this reader has, which is why the asking is driven by the
    last sample seen instead.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self, after_sequence: int = 0) -> TraceView:
        """Read everything recorded after the given sequence number."""
        collected: list[AnalogSample] = []
        position = after_sequence
        recorded = after_sequence
        for _ in range(MAXIMUM_PAGES):
            samples, recorded = self._session.read_trace(position)
            if not samples:
                break
            collected.extend(samples)
            position = samples[-1].sequence + 1
            if position >= recorded:
                break
        return build_trace_view(tuple(collected), max(recorded, position))
