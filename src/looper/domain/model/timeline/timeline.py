"""Every lane, on one ruler.

This is the whole point of the thing. A simulation already records
values, bus exchanges and adapter calls, each with a moment from the
same clock -- and shows them in three tabs, so that comparing them
means reading numbers off two screens and trusting your memory for
the third. Put on one axis they answer the question none of them
answers alone: in what order did this happen, and what happened at
the same time as what.

The timeline is the arrangement, not the drawing. It knows which rows
there are, what is on them, and which stretch of time they cover.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from looper.domain.model.timeline.lane import TimelineLane
from looper.domain.model.timeline.time_window import TimeWindow


@dataclass(frozen=True)
class Timeline:
    """The lanes of one recording, in the order they are worth reading.

    Attributes:
        lanes: The rows, in display order.
    """

    lanes: tuple[TimelineLane, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        keys = [lane.key for lane in self.lanes]
        if len(set(keys)) != len(keys):
            raise ValueError("Two lanes cannot share a key")

    @property
    def is_empty(self) -> bool:
        """Whether nothing was recorded on any lane."""
        return all(lane.is_empty for lane in self.lanes)

    @property
    def recorded(self) -> TimeWindow | None:
        """The stretch from the first thing that happened to the last.

        Returns:
            The window, or nothing when nothing happened. A caller
            showing an empty recording has to choose what to display,
            and a made up window would be the wrong choice made here.
        """
        return TimeWindow.spanning(self._ends())

    def _ends(self) -> Iterator[float]:
        """The first and the last moment of every lane that had any.

        Enough to span them all, and worth saying rather than
        handing over every moment there is: a lane's moments are in
        order, so nothing on it happened before its first or after
        its last, and a busy window holds tens of thousands of them.
        """
        for lane in self.lanes:
            if lane.moments:
                yield lane.moments[0]
                yield lane.moments[-1]

    def within(self, window: TimeWindow) -> Timeline:
        """The same lanes, holding only what the window shows.

        Every lane survives, including the ones with nothing in the
        window: a row that disappears when you pan past its traffic
        makes the rows below it jump, and a reader loses the one
        thing a shared ruler is for.
        """
        return Timeline(tuple(lane.within(window) for lane in self.lanes))

    def lane(self, key: str) -> TimelineLane | None:
        """The lane with this key, if there is one."""
        for one in self.lanes:
            if one.key == key:
                return one
        return None
