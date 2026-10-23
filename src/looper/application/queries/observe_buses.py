"""Use cases that read the buses of a running simulation."""

from __future__ import annotations

from looper.application.dto.bus_view import BusTraceView, BusView, ComponentView
from looper.application.mapping.bus_view import (
    build_bus_trace_view,
    build_bus_view,
    build_component_view,
)
from looper.domain.model.simulation import BusTraceEntry
from looper.domain.ports import SimulationSession

#: Replies one reading will take before giving up. One reply carries a
#: page of exchanges; a firmware that burst a few hundred frames while
#: nobody was reading needs several, and a client that was away for a
#: while needs more than that.
MAXIMUM_PAGES = 100


class ObserveBuses:
    """Reads every bus the simulation models."""

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self) -> tuple[BusView, ...]:
        """Take one snapshot of every bus."""
        return tuple(build_bus_view(bus) for bus in self._session.read_buses())


class ObserveComponents:
    """Reads every component attached to those buses."""

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self) -> tuple[ComponentView, ...]:
        """Take one snapshot of what is attached."""
        return tuple(
            build_component_view(component) for component in self._session.read_components()
        )


class ReadBusTrace:
    """Reads recorded exchanges incrementally.

    A list of what crossed needs every exchange, not only the ones
    that happened to fall on a poll. The simulation records them as
    they cross and this collects what is new since the last call.

    It keeps asking until it has caught up. One reply carries a page,
    and the sequence a reply reports as next is where the *recording*
    has got to rather than where this reader has -- so a reader that
    continued from it would step over everything in between, and a
    burst of traffic would simply be missing from the list.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self, after_sequence: int = 0) -> BusTraceView:
        """Read everything recorded after the given sequence number."""
        collected: list[BusTraceEntry] = []
        position = after_sequence
        recorded = after_sequence
        for _ in range(MAXIMUM_PAGES):
            entries, recorded = self._session.read_bus_trace(position)
            if not entries:
                break
            collected.extend(entries)
            position = entries[-1].sequence + 1
            if position >= recorded:
                break
        return build_bus_trace_view(tuple(collected), max(recorded, position))

    def clear(self) -> None:
        """Discard the recorded exchanges and start again."""
        self._session.clear_bus_trace()
