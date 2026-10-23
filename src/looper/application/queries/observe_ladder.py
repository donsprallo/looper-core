"""One bus, read as a conversation instead of a list.

The same records the bus table shows, arranged by who was talking.
Which bus is the caller's choice, because a ladder is read closely
and reading four at once is reading none of them.

Stateful for the same reason the timeline is: the trace is a ring
and a reply carries a page of it, so the only place a conversation
longer than one reply can exist is in the thing doing the reading.
"""

from __future__ import annotations

from collections import deque

from looper.application.dto.ladder_view import LadderView
from looper.application.mapping.ladder_view import build_ladder_view
from looper.domain.model.simulation import BusTraceEntry
from looper.domain.ports import SimulationSession

#: Turns a ladder keeps. A conversation is read a screen at a time
#: and nobody scrolls back through ten thousand; what is wanted is
#: the recent past in full rather than the whole run in part.
MAXIMUM_TURNS = 500

#: Replies one reading takes before giving up, as the bus table does.
MAXIMUM_PAGES = 100


class ObserveLadder:
    """Collects what crossed one bus and arranges it by who spoke."""

    def __init__(self, session: SimulationSession) -> None:
        self._session = session
        self._exchanges: deque[BusTraceEntry] = deque(maxlen=MAXIMUM_TURNS)
        self._position = 0
        self._bus: int | None = None

    @property
    def bus(self) -> int | None:
        """The bus being listened to, or nothing when none was chosen."""
        return self._bus

    def listen_to(self, bus: int | None) -> None:
        """Follow another bus, forgetting what the last one said."""
        if bus == self._bus:
            return
        self._bus = bus
        self._exchanges.clear()

    def execute(self) -> LadderView:
        """Read what is new and hand back the whole conversation."""
        if self._bus is None:
            return LadderView()
        self._take_exchanges()
        buses = {one.identifier: one for one in self._session.read_buses()}
        chosen = buses.get(self._bus)
        return build_ladder_view(
            bus_name=chosen.label if chosen is not None else "",
            exchanges=tuple(self._exchanges),
            components=self._session.read_components(),
        )

    def clear(self) -> None:
        """Forget what has been collected and start again."""
        self._exchanges.clear()
        self._position = 0

    def _take_exchanges(self) -> None:
        """Read what crossed since the last reading, keeping this bus."""
        for _ in range(MAXIMUM_PAGES):
            entries, recorded = self._session.read_bus_trace(self._position)
            if not entries:
                break
            self._exchanges.extend(one for one in entries if one.bus == self._bus)
            self._position = entries[-1].sequence + 1
            if self._position >= recorded:
                break
